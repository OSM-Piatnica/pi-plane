# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Work item types of a project: shared get-or-create and link code, and the per-project Epics switch.

A type is usable in a project only through a `ProjectIssueType` link, so "Epics are on" means that a type with
`is_epic` is linked to the project. Nothing here assumes that Epic and Task are the only special types.
"""

from django.db import IntegrityError, transaction

from plane.db.models import Issue, IssueType, Project, ProjectIssueType

EPIC_TYPE_NAME = "Epic"
EPIC_LEVEL = 1


class EpicsNotAvailableError(Exception):
    """Epics cannot be switched on for a project that does not use work item types."""


def get_or_create_issue_type(
    *, workspace_id, name: str, description: str = "", is_epic: bool, is_default: bool, created_by_id=None
):
    """The active type of the workspace with this name, created when there is none."""

    cleaned_name = (name or "").strip()[:255]
    if not cleaned_name:
        return None
    existing = IssueType.objects.filter(workspace_id=workspace_id, name=cleaned_name, deleted_at__isnull=True).first()
    if existing:
        return existing
    try:
        with transaction.atomic():
            return IssueType.objects.create(
                workspace_id=workspace_id,
                name=cleaned_name,
                description=str(description or "")[:4096],
                is_epic=is_epic,
                is_default=is_default,
                created_by_id=created_by_id,
            )
    except IntegrityError:
        return IssueType.objects.filter(workspace_id=workspace_id, name=cleaned_name, deleted_at__isnull=True).first()


def link_issue_type_to_project(project: Project, issue_type, *, level: int, is_default: bool, created_by_id=None):
    """Make the type usable in the project. Linking an already linked type changes nothing."""

    if issue_type is None:
        return None
    existing = ProjectIssueType.objects.filter(project=project, issue_type=issue_type, deleted_at__isnull=True).first()
    if existing:
        return existing
    try:
        with transaction.atomic():
            return ProjectIssueType.objects.create(
                project=project,
                issue_type=issue_type,
                workspace_id=project.workspace_id,
                level=level,
                is_default=is_default,
                created_by_id=created_by_id,
            )
    except IntegrityError:
        return ProjectIssueType.objects.filter(project=project, issue_type=issue_type, deleted_at__isnull=True).first()


def linked_epic_types(project: Project):
    return IssueType.objects.filter(
        project_issue_types__project=project,
        project_issue_types__deleted_at__isnull=True,
        is_epic=True,
        is_active=True,
        deleted_at__isnull=True,
    ).distinct()


def project_epics_enabled(project: Project) -> bool:
    return linked_epic_types(project).exists()


def workspace_epic_type(workspace_id, *, created_by_id=None):
    """The Epic type the switch uses: the oldest active `is_epic` type, created when the workspace has none.

    Other `is_epic` types that admins made stay usable through the normal type linking.
    """

    existing = (
        IssueType.objects.filter(workspace_id=workspace_id, is_epic=True, is_active=True, deleted_at__isnull=True)
        .order_by("created_at", "id")
        .first()
    )
    if existing:
        return existing
    # A non-Epic type may already own the name, so the new one gets a free name
    name = EPIC_TYPE_NAME
    if IssueType.objects.filter(workspace_id=workspace_id, name=name, deleted_at__isnull=True).exists():
        name = f"{EPIC_TYPE_NAME} work item"
    return get_or_create_issue_type(
        workspace_id=workspace_id, name=name, is_epic=True, is_default=False, created_by_id=created_by_id
    )


def ensure_project_epic_type(project: Project, *, created_by_id=None, require_types_enabled: bool = True):
    """Turn Epics on: link the workspace's Epic type to the project. Returns the type."""

    if require_types_enabled and not project.is_issue_type_enabled:
        raise EpicsNotAvailableError("Work item types are not enabled for this project")
    epic_type = workspace_epic_type(project.workspace_id, created_by_id=created_by_id)
    link_issue_type_to_project(project, epic_type, level=EPIC_LEVEL, is_default=False, created_by_id=created_by_id)
    return epic_type


def remove_project_epic_types(project: Project) -> int:
    """Turn Epics off: unlink every Epic type from the project.

    Work items that already have an Epic type and their children stay as they are; only new Epics and a change of
    type to an Epic stop. Linking the type again restores everything. Returns the number of links removed.
    """

    links = ProjectIssueType.objects.filter(
        project=project,
        deleted_at__isnull=True,
        issue_type__is_epic=True,
    )
    removed = 0
    with transaction.atomic():
        for link in links:
            link.delete()
            removed += 1
    return removed


def issue_type_in_use(issue_type: IssueType) -> bool:
    return Issue.all_objects.filter(type=issue_type).exists()


def issue_type_assignment_error(project_id, issue_type, current_type=None):
    """Why a work item cannot be given this type in this project, or None when it can.

    A work item keeps the type it already has, so one that is an Epic stays editable after Epics were turned off.
    """

    if issue_type is None or (current_type is not None and current_type.id == issue_type.id):
        return None
    if not ProjectIssueType.objects.filter(
        project_id=project_id,
        issue_type_id=issue_type.id,
        deleted_at__isnull=True,
        issue_type__is_active=True,
        issue_type__deleted_at__isnull=True,
    ).exists():
        return "Issue type is not enabled for this project"
    if not Project.objects.filter(pk=project_id, is_issue_type_enabled=True).exists():
        return "Work item types are not enabled for this project"
    return None
