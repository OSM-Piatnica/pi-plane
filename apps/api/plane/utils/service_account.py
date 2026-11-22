# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Service accounts: the bot behind the bot tokens that instance admins create in God Mode.

Each workspace has at most one service account. It is a bot user (it cannot sign in) that is a member of the
workspace and of every project in it, so its API tokens read everything the public API shows, in all projects,
including the ones created later. Its tokens are read-only (see plane.api.middleware.api_authentication).
"""

# Python imports
import logging
from urllib.parse import urlparse
from uuid import uuid4

# Django imports
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

# Module imports
from plane.db.models import BotTypeEnum, Project, ProjectMember, User, WorkspaceMember
from plane.utils.permissions import ROLE

# Member, not Admin: enough to see every work item, state, comment and member of a project
SERVICE_ACCOUNT_ROLE = ROLE.MEMBER.value
SERVICE_ACCOUNT_NAME = "Pi-Plane API"

logger = logging.getLogger("plane.api")


class ServiceAccountDisabled(Exception):
    """The workspace's service account was deactivated; creating a token must not silently bring it back."""


def is_service_account(user) -> bool:
    return bool(user and user.is_bot and user.bot_type == BotTypeEnum.SERVICE_ACCOUNT)


def _username(workspace_id) -> str:
    return f"service_account_{workspace_id}"


def get_service_account(workspace_id):
    return User.objects.filter(
        username=_username(workspace_id), is_bot=True, bot_type=BotTypeEnum.SERVICE_ACCOUNT
    ).first()


@transaction.atomic
def get_or_create_service_account(workspace):
    """The workspace's service account, created when missing and made an active member of the workspace."""
    user = get_service_account(workspace.id)
    if user is None:
        host = urlparse(settings.WEB_URL or "https://plane.so").hostname or "plane.so"
        try:
            # a savepoint, so that losing the race for the unique username does not break the outer transaction
            with transaction.atomic():
                user = User.objects.create(
                    username=_username(workspace.id),
                    email=f"{_username(workspace.id)}@{host}",
                    display_name=SERVICE_ACCOUNT_NAME,
                    first_name=SERVICE_ACCOUNT_NAME,
                    last_name="",
                    is_bot=True,
                    bot_type=BotTypeEnum.SERVICE_ACCOUNT,
                    password=make_password(uuid4().hex),
                    is_password_autoset=True,
                )
        except IntegrityError:
            # another request created it first
            user = get_service_account(workspace.id)
            if user is None:
                raise
    if not user.is_active:
        raise ServiceAccountDisabled(workspace.id)

    workspace_member = WorkspaceMember.objects.filter(workspace=workspace, member=user).first()
    if workspace_member is None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=SERVICE_ACCOUNT_ROLE, company_role="")
    elif not workspace_member.is_active or workspace_member.role != SERVICE_ACCOUNT_ROLE:
        workspace_member.is_active = True
        workspace_member.role = SERVICE_ACCOUNT_ROLE
        workspace_member.save(update_fields=["is_active", "role", "updated_at"])
    return user


def _join(user, projects) -> int:
    """Make ``user`` an active member of ``projects``. Returns how many memberships it created or restored."""
    projects = list(projects)
    if not projects:
        return 0
    rows = {
        row.project_id: row
        for row in ProjectMember.objects.filter(member=user, project_id__in=[project.id for project in projects])
    }
    changed = 0
    for project in projects:
        row = rows.get(project.id)
        if row is None:
            # save() of a new member also adds the ProjectUserProperty every member has
            ProjectMember.objects.create(project=project, member=user, role=SERVICE_ACCOUNT_ROLE)
            changed += 1
        elif not row.is_active or row.role != SERVICE_ACCOUNT_ROLE:
            row.is_active = True
            row.role = SERVICE_ACCOUNT_ROLE
            row.save(update_fields=["is_active", "role", "updated_at"])
            changed += 1
    return changed


@transaction.atomic
def sync_service_account_projects(user, workspace_id) -> int:
    """Make the service account a member of every project of the workspace (archived ones too)."""
    return _join(user, Project.objects.filter(workspace_id=workspace_id))


@receiver(post_save, sender=Project)
def add_service_account_to_new_project(sender, instance, created, raw=False, **kwargs):
    """The workspace's service account joins every new project, so God Mode bot tokens see all projects.

    A failure here must not stop the project from being created; the next token creation syncs the memberships."""
    if not created or raw:
        return
    try:
        with transaction.atomic():
            add_service_accounts_to_project(instance)
    except Exception:
        logger.exception("Could not add the service account to project %s", instance.id)


def add_service_accounts_to_project(project) -> None:
    """A new project gets the service account of its workspace, so bot tokens see it right away."""
    accounts = User.objects.filter(
        username=_username(project.workspace_id),
        is_bot=True,
        bot_type=BotTypeEnum.SERVICE_ACCOUNT,
        is_active=True,
        member_workspace__workspace_id=project.workspace_id,
        member_workspace__is_active=True,
        member_workspace__deleted_at__isnull=True,
    )
    for user in accounts:
        _join(user, [project])


def service_account_project_count(user) -> int:
    return ProjectMember.objects.filter(member=user, is_active=True).count()
