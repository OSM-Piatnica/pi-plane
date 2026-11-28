# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Work item types of a project: shared get-or-create and link code, and the per-project Epics switch.

A type is usable in a project only through a `ProjectIssueType` link, so "Epics are on" means that a type of the
Epic kind is linked to the project. The same holds for every kind with special behaviour (`IssueTypeKind`): one
type per kind is found or created for the workspace and linked to the project on demand.
"""

from django.db import IntegrityError, transaction
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from plane.db.models import (
    ISSUE_TYPE_KIND_LEVELS,
    SYSTEM_MANAGED_ISSUE_TYPE_KINDS,
    Issue,
    IssueType,
    IssueTypeKind,
    Project,
    ProjectIssueType,
    Workspace,
)

# The name a kind's type gets when the workspace has none yet; admins can rename it afterwards
KIND_TYPE_NAMES = {
    IssueTypeKind.EPIC: "Epic",
    IssueTypeKind.MILESTONE: "Milestone",
    IssueTypeKind.APPROVAL: "Approval",
    IssueTypeKind.REVIEW: "Review",
}
EPIC_TYPE_NAME = KIND_TYPE_NAMES[IssueTypeKind.EPIC]
EPIC_LEVEL = ISSUE_TYPE_KIND_LEVELS[IssueTypeKind.EPIC]

SYSTEM_MANAGED_TYPE_CODE = "WORK_ITEM_TYPE_SYSTEM_MANAGED"


class WorkItemTypesNotEnabledError(Exception):
    """A kind's type cannot be linked to a project that does not use work item types."""


# The name the Epics switch has always raised
EpicsNotAvailableError = WorkItemTypesNotEnabledError


class IssueTypeAssignmentError(str):
    """The reason a type cannot be assigned, with an `error_code` a client can act on."""

    error_code = None

    def __new__(cls, message: str, error_code=None):
        instance = super().__new__(cls, message)
        instance.error_code = error_code
        return instance


class IssueTypeChangeRejected(APIException):
    """Answers 400 with the payload as it is, like ``ParentReopenRequired``: a client looks for ``error_code``."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, payload: dict):
        self.detail = payload


def raise_issue_type_assignment_error(error, *, field=None):
    """Answer with a reason from `issue_type_assignment_error`: a coded reason keeps its code in the body."""

    if getattr(error, "error_code", None):
        raise IssueTypeChangeRejected({"error": str(error), "error_code": error.error_code})
    raise serializers.ValidationError({field: str(error)} if field else str(error))


def is_system_managed_type(issue_type) -> bool:
    return issue_type is not None and issue_type.kind in SYSTEM_MANAGED_ISSUE_TYPE_KINDS


# What a client may not do by hand to a system-managed type (approval, review). The feature that owns such a type
# links it through `ensure_project_kind_type`, which works on the models and never meets these checks.
SYSTEM_MANAGED_TYPE_DELETE = "delete"
SYSTEM_MANAGED_TYPE_DEACTIVATE = "deactivate"
SYSTEM_MANAGED_TYPE_LINK = "link"
SYSTEM_MANAGED_TYPE_UNLINK = "unlink"
SYSTEM_MANAGED_TYPE_CHANGE_PROJECTS = "change_projects"
SYSTEM_MANAGED_TYPE_MAKE_DEFAULT = "make_default"

_SYSTEM_MANAGED_TYPE_MESSAGES = {
    SYSTEM_MANAGED_TYPE_DELETE: "A system-managed work item type (approval, review) cannot be deleted",
    SYSTEM_MANAGED_TYPE_DEACTIVATE: "A system-managed work item type (approval, review) cannot be deactivated",
    SYSTEM_MANAGED_TYPE_LINK: "A system-managed work item type (approval, review) cannot be added to a project by hand",
    SYSTEM_MANAGED_TYPE_UNLINK: "A system-managed work item type (approval, review) cannot be removed from a project",
    SYSTEM_MANAGED_TYPE_CHANGE_PROJECTS: (
        "The projects of a system-managed work item type (approval, review) cannot be changed by hand"
    ),
    SYSTEM_MANAGED_TYPE_MAKE_DEFAULT: (
        "A system-managed work item type (approval, review) cannot be the default type of a project"
    ),
}


def refuse_system_managed_type(issue_type, action: str) -> None:
    """Answer 400 with the `SYSTEM_MANAGED_TYPE_CODE` error code when `issue_type` is system-managed.

    `action` is one of the `SYSTEM_MANAGED_TYPE_*` actions above; it picks the fixed message. Works from a view and
    from a serializer's `validate` (the error is an `APIException`, so DRF answers with the payload as it is).
    """

    if is_system_managed_type(issue_type):
        raise IssueTypeChangeRejected(
            {"error": _SYSTEM_MANAGED_TYPE_MESSAGES[action], "error_code": SYSTEM_MANAGED_TYPE_CODE}
        )


def get_or_create_issue_type(
    *,
    workspace_id,
    name: str,
    description: str = "",
    is_epic: bool = False,
    is_default: bool,
    created_by_id=None,
    kind=None,
):
    """The active type of the workspace with this name, created when there is none.

    `kind` decides what a new type is; `is_epic` is the older way to ask for the Epic kind.
    """

    if kind is None:
        kind = IssueTypeKind.EPIC if is_epic else IssueTypeKind.STANDARD

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
                kind=kind,
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


def _system_kind(kind) -> IssueTypeKind:
    """`kind` as one of the kinds that have a system type; the standard kind has none."""

    kind = IssueTypeKind(kind)
    if kind not in KIND_TYPE_NAMES:
        raise ValueError(f"The {kind} kind has no system work item type")
    return kind


def linked_kind_types(project: Project, kind):
    return IssueType.objects.filter(
        project_issue_types__project=project,
        project_issue_types__deleted_at__isnull=True,
        kind=IssueTypeKind(kind),
        is_active=True,
        deleted_at__isnull=True,
    ).distinct()


def linked_epic_types(project: Project):
    return linked_kind_types(project, IssueTypeKind.EPIC)


def project_epics_enabled(project: Project) -> bool:
    return linked_epic_types(project).exists()


def _workspace_kind_types(workspace_id, kind):
    return IssueType.objects.filter(
        workspace_id=workspace_id, kind=kind, is_active=True, deleted_at__isnull=True
    ).order_by("created_at", "id")


def workspace_kind_type(workspace_id, kind, *, created_by_id=None, name=None, defaults=None):
    """The type of this kind that the system uses: the oldest active one, created when the workspace has none.

    Other types of the kind that admins made stay usable through the normal type linking. `name` is the name a new
    type gets (the name of the kind when left out) and `defaults` are further fields of a new type (the type
    catalogue passes its icon and description template); neither changes a type that already exists.
    """

    kind = _system_kind(kind)
    existing = _workspace_kind_types(workspace_id, kind).first()
    if existing:
        return existing
    with transaction.atomic():
        # Creation takes turns per workspace: two requests that both found no type would each make one. The lock
        # is on the workspace row and held to the end of the caller's transaction; the second request then finds
        # the type the first one made. (No unique constraint: a workspace may hold several types of a kind.)
        Workspace.objects.select_for_update().filter(pk=workspace_id).values_list("id", flat=True).first()
        existing = _workspace_kind_types(workspace_id, kind).first()
        if existing:
            return existing
        # A type of another kind may already own the name, so the new one gets a free name
        name = (name or "").strip()[:255] or KIND_TYPE_NAMES[kind]
        if IssueType.objects.filter(workspace_id=workspace_id, name__iexact=name, deleted_at__isnull=True).exists():
            name = f"{name} work item"
        if IssueType.objects.filter(workspace_id=workspace_id, name__iexact=name, deleted_at__isnull=True).exists():
            # The second name is taken by a type of another kind as well. A kind drives behaviour, so no kind
            # (the Epic kind included) is ever handed a type of the wrong kind
            name = f"{name} ({kind})"
        return IssueType.objects.create(
            workspace_id=workspace_id,
            name=name[:255],
            kind=kind,
            is_default=False,
            created_by_id=created_by_id,
            **(defaults or {}),
        )


def workspace_epic_type(workspace_id, *, created_by_id=None):
    """The Epic type the Epics switch uses."""

    return workspace_kind_type(workspace_id, IssueTypeKind.EPIC, created_by_id=created_by_id)


def ensure_project_kind_type(project: Project, kind, *, created_by_id=None, require_types_enabled: bool = True):
    """Link the workspace's type of this kind to the project, creating the type when needed. Returns the type."""

    kind = _system_kind(kind)
    if require_types_enabled and not project.is_issue_type_enabled:
        raise WorkItemTypesNotEnabledError("Work item types are not enabled for this project")
    kind_type = workspace_kind_type(project.workspace_id, kind, created_by_id=created_by_id)
    link_issue_type_to_project(
        project,
        kind_type,
        # The link stores a non-negative level; the hierarchy rules read the level of the kind, not this one
        level=max(ISSUE_TYPE_KIND_LEVELS[kind], 0),
        is_default=False,
        created_by_id=created_by_id,
    )
    return kind_type


def ensure_project_epic_type(project: Project, *, created_by_id=None, require_types_enabled: bool = True):
    """Turn Epics on: link the workspace's Epic type to the project. Returns the type."""

    return ensure_project_kind_type(
        project, IssueTypeKind.EPIC, created_by_id=created_by_id, require_types_enabled=require_types_enabled
    )


def remove_project_epic_types(project: Project) -> int:
    """Turn Epics off: unlink every Epic type from the project.

    Work items that already have an Epic type and their children stay as they are; only new Epics and a change of
    type to an Epic stop. Linking the type again restores everything. Returns the number of links removed.
    """

    links = ProjectIssueType.objects.filter(
        project=project,
        deleted_at__isnull=True,
        issue_type__kind=IssueTypeKind.EPIC,
    )
    removed = 0
    with transaction.atomic():
        for link in links:
            link.delete()
            removed += 1
    return removed


def issue_type_in_use(issue_type: IssueType) -> bool:
    return Issue.all_objects.filter(type=issue_type).exists()


def issue_type_assignment_error(project_id, issue_type, current_type=None, *, existing=None):
    """Why a work item cannot be given this type in this project, or None when it can.

    A work item keeps the type it already has, so one that is an Epic stays editable after Epics were turned off.
    `existing` says that the work item is already saved (by default: when it has a type). An existing work item
    cannot be switched into or out of a system-managed kind (approval, review); that reason carries the
    `error_code` `SYSTEM_MANAGED_TYPE_CODE`. A new work item can be created with such a type.

    `issue_type` is None when the type is cleared. Call this whenever a type was sent, None included: taking the
    type off an approval or review work item is a switch out of the kind too.
    """

    if (issue_type.id if issue_type else None) == (current_type.id if current_type else None):
        return None
    if existing is None:
        existing = current_type is not None
    if existing and (is_system_managed_type(issue_type) or is_system_managed_type(current_type)):
        return IssueTypeAssignmentError(
            "The type of a work item cannot be changed to or from a system-managed type (approval, review)",
            SYSTEM_MANAGED_TYPE_CODE,
        )
    if issue_type is None:
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
