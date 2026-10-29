# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Mirrors the groups a person has at their identity provider as user groups that are managed outside.

The provider is the only source of these groups: people are put in and taken out of them here as the provider says,
and nobody can change them by hand. The groups appear in every workspace the person belongs to. What was read at the
last sign-in is kept on the person's account, so that a workspace they join later gets their groups at once.
"""

import logging

from django.db import transaction
from django.utils import timezone

from plane.db.models import Account, GroupRole, GroupSource, UserGroup, UserGroupMember, WorkspaceMember

logger = logging.getLogger("plane.authentication")

SOURCE_LABELS = {GroupSource.ENTRA: "Entra", GroupSource.GOOGLE: "Google", GroupSource.OIDC: "SSO"}
STORED_KEY = "external_groups"


def _free_name(workspace_id, source, wanted, external_id, existing_id=None):
    """The name to give a group: the provider's, unless a sibling already has it (then a clarified one)."""
    taken = UserGroup.objects.filter(workspace_id=workspace_id, parent__isnull=True)
    if existing_id:
        taken = taken.exclude(pk=existing_id)
    candidates = [
        wanted[:255],
        f"{wanted[:230]} ({SOURCE_LABELS.get(source, source)})",
        f"{wanted[:200]} ({external_id[:40]})",
    ]
    for candidate in candidates:
        if not taken.filter(name__iexact=candidate).exists():
            return candidate
    return candidates[-1]


def _sync_workspace(workspace_id, user, source, groups):
    """Bring one workspace in line with the person's groups at the provider."""
    wanted = {group["id"]: group["name"] for group in groups}
    existing = {
        group.external_id: group
        for group in UserGroup.objects.filter(workspace_id=workspace_id, source=source, external_id__isnull=False)
    }

    current = set()
    for external_id, name in wanted.items():
        group = existing.get(external_id)
        if group is None:
            group = UserGroup.objects.create(
                workspace_id=workspace_id,
                source=source,
                external_id=external_id,
                name=_free_name(workspace_id, source, name, external_id),
            )
            existing[external_id] = group
        elif (
            group.name != name
            and not UserGroup.objects.filter(workspace_id=workspace_id, parent_id=group.parent_id, name__iexact=name)
            .exclude(pk=group.pk)
            .exists()
        ):
            # The provider renamed it; a name a sibling already uses is left alone
            group.name = name
            group.save(update_fields=["name", "updated_at"])
        current.add(group.id)
        if not UserGroupMember.objects.filter(group=group, user=user).exists():
            UserGroupMember.objects.create(
                workspace_id=workspace_id,
                group=group,
                user=user,
                role=GroupRole.MEMBER,
                managed_externally=True,
            )

    # Left at the provider: only what this sync put in is taken out
    UserGroupMember.objects.filter(
        workspace_id=workspace_id,
        user=user,
        managed_externally=True,
        group__source=source,
    ).exclude(group_id__in=current).delete()


def sync_external_groups(user, source, groups):
    """
    Mirror ``groups`` (ExternalGroup items) as the person's groups of ``source`` in all of their workspaces.

    ``None`` means the groups could not be read this time, and nothing changes.
    """
    if groups is None:
        return
    data = [{"id": group.id, "name": group.name} for group in groups]
    # The person's last known groups belong to the provider account they signed in with
    account = Account.objects.filter(user=user, provider=_provider_key(source)).first()
    if account is not None:
        account.metadata = {
            **(account.metadata or {}),
            STORED_KEY: data,
            f"{STORED_KEY}_at": timezone.now().isoformat(),
        }
        account.save(update_fields=["metadata", "updated_at"])
    workspace_ids = list(
        WorkspaceMember.objects.filter(member=user, is_active=True).values_list("workspace_id", flat=True)
    )
    for workspace_id in workspace_ids:
        with transaction.atomic():
            _sync_workspace(workspace_id, user, source, data)


def sync_workspace_from_stored(user, workspace_id):
    """A person who joins a workspace gets the groups their provider reported at their last sign-in."""
    for source in (GroupSource.ENTRA, GroupSource.GOOGLE, GroupSource.OIDC):
        account = Account.objects.filter(user=user, provider=_provider_key(source)).first()
        stored = (account.metadata or {}).get(STORED_KEY) if account else None
        if stored:
            with transaction.atomic():
                _sync_workspace(workspace_id, user, source, stored)


def _provider_key(source):
    """The Account.provider a group source is read through."""
    return {GroupSource.ENTRA: "entra", GroupSource.GOOGLE: "google-oidc", GroupSource.OIDC: "oidc"}[source]
