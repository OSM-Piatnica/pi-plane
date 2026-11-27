# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from django.db import IntegrityError

from plane.db.models import SYSTEM_MANAGED_ISSUE_TYPE_KINDS, IssueType, IssueTypeProperty, Project
from plane.utils.issue_type_property import clean_property_list
from plane.utils.project_issue_types import (
    ensure_project_epic_type,
    get_or_create_issue_type,
    link_issue_type_to_project,
)

logger = logging.getLogger("plane.api")


def _system_managed_type_names(workspace_id) -> set:
    """Lower-case names of the workspace's system-managed types (approval, review)."""

    return {
        name.lower()
        for name in IssueType.objects.filter(
            workspace_id=workspace_id, kind__in=SYSTEM_MANAGED_ISSUE_TYPE_KINDS, deleted_at__isnull=True
        ).values_list("name", flat=True)
    }


def seed_project_issue_types_from_template_payload(
    *,
    project: Project,
    payload: dict,
    created_by_id,
) -> list[str]:
    """Link the template's work item types to the project, creating the ones the workspace does not have yet.

    Types are found by name. A name that belongs to a system-managed type (approval, review) is skipped: only the
    feature that owns such a type links it, and a second type with the same name would be a duplicate. Returns the
    template names that were skipped, so the caller can report them; the rest of the template is applied.
    """

    skipped: list[str] = []
    if not payload.get("is_issue_type_enabled"):
        return skipped
    if not getattr(project, "is_issue_type_enabled", False):
        return skipped

    ws_id = project.workspace_id
    system_managed_names = _system_managed_type_names(ws_id)

    def _is_skipped(name: str) -> bool:
        if name.strip()[:255].lower() not in system_managed_names:
            return False
        skipped.append(name)
        logger.info(
            "Project template entry skipped: the name belongs to a system-managed work item type",
            extra={"project_id": str(project.id)},
        )
        return True

    def _get_or_create_issue_type(*, name: str, description: str = "", is_epic: bool, is_default: bool):
        return get_or_create_issue_type(
            workspace_id=ws_id,
            name=name,
            description=description,
            is_epic=is_epic,
            is_default=is_default,
            created_by_id=created_by_id,
        )

    def _seed_properties(issue_type: IssueType | None, raw_properties):
        if issue_type is None or not raw_properties:
            return
        try:
            rows = clean_property_list(raw_properties)
        except ValueError:
            return
        for idx, row in enumerate(rows):
            exists = IssueTypeProperty.objects.filter(
                issue_type=issue_type,
                title=row["title"],
                deleted_at__isnull=True,
            ).first()
            if exists:
                continue
            try:
                IssueTypeProperty.objects.create(
                    workspace_id=issue_type.workspace_id,
                    issue_type=issue_type,
                    title=row["title"],
                    description=row.get("description", ""),
                    property_type=row["property_type"],
                    is_mandatory=row.get("is_mandatory", False),
                    is_active=row.get("is_active", True),
                    options=row.get("options", []),
                    select_mode=row.get("select_mode", "single"),
                    default_value=row.get("default_value"),
                    sort_order=(idx + 1) * 10000,
                    created_by_id=created_by_id,
                )
            except IntegrityError:
                pass

    def _link(project_: Project, issue_type: IssueType | None, *, level: int, is_default: bool):
        link_issue_type_to_project(
            project_, issue_type, level=level, is_default=is_default, created_by_id=created_by_id
        )

    if not _is_skipped("Task"):
        task_type = _get_or_create_issue_type(name="Task", is_epic=False, is_default=True)
        _link(project, task_type, level=0, is_default=True)
        _seed_properties(task_type, payload.get("task_custom_properties"))

    if payload.get("epic_enabled"):
        epic_type = ensure_project_epic_type(project, created_by_id=created_by_id)
        _seed_properties(epic_type, payload.get("epic_custom_properties"))

    extra = payload.get("additional_work_item_types") or []
    if not isinstance(extra, list):
        return skipped
    base_level = 2
    for idx, row in enumerate(extra[:20]):
        if not isinstance(row, dict):
            continue
        nm = str(row.get("name", "")).strip()[:255]
        if not nm:
            continue
        if nm.lower() in {"task", "epic"}:
            continue
        if _is_skipped(nm):
            continue
        desc = str(row.get("description", "") or "")[:4096]
        it = _get_or_create_issue_type(name=nm, description=desc, is_epic=False, is_default=False)
        _link(project, it, level=base_level + idx, is_default=False)
        _seed_properties(it, row.get("custom_properties"))
    return skipped
