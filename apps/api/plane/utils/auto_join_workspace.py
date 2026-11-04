# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Joining the company workspace without an invite.

The instance admin picks one workspace and the email domains of the company (admin app, Workspaces). Everybody who
signs in to the app with an address of one of those domains and has never been a member of that workspace becomes one,
so that signing up from the bare address of the instance no longer ends in a workspace of one's own. The settings:

* ``AUTO_JOIN_WORKSPACE_ID``: the workspace; empty turns the feature off;
* ``AUTO_JOIN_WORKSPACE_ROLE``: the role people get, Member (15, the default) or Guest (5);
* ``AUTO_JOIN_EMAIL_DOMAINS``: the domains, separated by commas; empty also turns the feature off.

An invite to the workspace still decides the role. A membership that exists, active or not, is left alone, so a person
an admin removed or suspended does not come back by signing in again.
"""

import os
import re
import uuid

from django.db import transaction

from plane.db.models import Profile, Workspace, WorkspaceMember, WorkspaceMemberInvite
from plane.utils.cache import invalidate_cache_directly

WORKSPACE_KEY = "AUTO_JOIN_WORKSPACE_ID"
ROLE_KEY = "AUTO_JOIN_WORKSPACE_ROLE"
DOMAINS_KEY = "AUTO_JOIN_EMAIL_DOMAINS"

# Admin (20) is never handed out without somebody choosing it in an invite
ALLOWED_ROLES = {"5": 5, "15": 15}
DEFAULT_ROLE = 15

_DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def parse_domains(raw):
    """The domains of a setting value: lower case, without a leading @, empty entries dropped."""
    return [d for d in (part.strip().lower().lstrip("@") for part in str(raw or "").split(",")) if d]


def invalid_domains(raw):
    """The entries of a setting value that are not domain names."""
    return [d for d in parse_domains(raw) if not _DOMAIN.match(d)]


def parse_role(raw):
    """The role of a setting value, or None when it is not one that may be handed out."""
    raw = str(raw or "").strip()
    if not raw:
        return DEFAULT_ROLE
    return ALLOWED_ROLES.get(raw)


def get_auto_join_settings():
    """(workspace, role, domains) when the feature is set up, otherwise None."""
    from plane.license.utils.instance_value import get_configuration_value

    workspace_id, role, domains = get_configuration_value(
        [
            {"key": WORKSPACE_KEY, "default": os.environ.get(WORKSPACE_KEY, "")},
            {"key": ROLE_KEY, "default": os.environ.get(ROLE_KEY, str(DEFAULT_ROLE))},
            {"key": DOMAINS_KEY, "default": os.environ.get(DOMAINS_KEY, "")},
        ]
    )
    domains = parse_domains(domains)
    role = parse_role(role)
    if not domains or role is None:
        return None
    try:
        workspace_id = uuid.UUID(str(workspace_id or "").strip())
    except ValueError:
        return None
    workspace = Workspace.objects.filter(id=workspace_id).first()
    if workspace is None:
        return None
    return workspace, role, domains


def is_eligible(user, workspace, domains):
    """Whether the user would join: an active person (no bot) of one of the domains, never a member of the workspace."""
    if not user.is_active or user.is_bot or not user.email:
        return False
    if user.email.rsplit("@", 1)[-1].lower() not in domains:
        return False
    # The default manager leaves out soft-deleted rows only: removed and suspended members still count
    return not WorkspaceMember.objects.filter(workspace=workspace, member=user).exists()


def join_auto_join_workspace(user, settings=None):
    """Make the user a member of the company workspace if they qualify. Returns the new membership or None."""
    settings = settings or get_auto_join_settings()
    if settings is None:
        return None
    workspace, role, domains = settings
    if not is_eligible(user, workspace, domains):
        return None

    invites = WorkspaceMemberInvite.objects.filter(workspace=workspace, email__iexact=user.email)
    invite = invites.order_by("-created_at").first()

    with transaction.atomic():
        # .create (not bulk_create): joining mirrors the person's groups and what they give in projects (signals)
        member = WorkspaceMember.objects.create(workspace=workspace, member=user, role=invite.role if invite else role)
        invites.delete()

        # Land in the workspace after signing in, and skip the step that asks to create or join one
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.last_workspace_id = workspace.id
        profile.onboarding_step = {**(profile.onboarding_step or {}), "workspace_join": True}
        profile.save(update_fields=["last_workspace_id", "onboarding_step", "updated_at"])

    invalidate_cache_directly(
        path=f"/api/workspaces/{workspace.slug}/members/", url_params=False, user=False, multiple=True
    )
    return member
