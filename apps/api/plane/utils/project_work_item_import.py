# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026 Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

import json

from django.db import transaction
from django.db.models import Max

from plane.db.models import (
    Issue,
    IssueActivity,
    IssueAssignee,
    IssueLabel,
    IssuePropertyValue,
    IssueSequence,
    IssueType,
    Label,
    Project,
    ProjectIssueType,
    ProjectMember,
    State,
    WorkspaceMember,
)
from plane.utils.html_processor import strip_tags
from plane.utils.issue_type_property import validate_property_value
from plane.utils.work_item_duration import (
    normalize_work_item_duration,
    reconcile_work_item_duration,
    to_work_item_date,
)

MAX_WORK_ITEMS_IMPORT = 500
ALLOWED_PRIORITIES = frozenset({"urgent", "high", "medium", "low", "none"})


def _coerce_list(value) -> list:
    if value in [None, ""]:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                return parsed if isinstance(parsed, list) else [text]
            except (json.JSONDecodeError, TypeError):
                pass
        return [part.strip() for part in text.split(",") if part.strip()]
    return []


def _coerce_dict(value) -> dict:
    if value in [None, ""]:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _normalize_description_html(raw) -> str:
    if raw in [None, ""]:
        return "<p></p>"
    text = str(raw).strip()
    if not text:
        return "<p></p>"
    if "<" in text and ">" in text:
        return text
    return f"<p>{text}</p>"


def import_work_items_into_project(
    *,
    project: Project,
    user,
    rows: list[dict],
    warnings: list[str] | None = None,
) -> dict:
    """Create work items from export rows (two-pass for parent links)."""
    warnings = warnings if warnings is not None else []

    if not rows:
        return {"created_work_items": 0, "warnings": warnings}

    if len(rows) > MAX_WORK_ITEMS_IMPORT:
        raise ValueError(
            {
                "error": (
                    f"Import contains more than {MAX_WORK_ITEMS_IMPORT} work items. "
                    "Reduce the file size or split the import."
                )
            }
        )

    states_by_name = {
        state.name.lower(): state
        for state in State.objects.filter(project_id=project.id, deleted_at__isnull=True, is_triage=False)
    }
    default_state = next((s for s in states_by_name.values() if s.default), None)
    if default_state is None and states_by_name:
        default_state = next(iter(states_by_name.values()))

    labels_by_name = {
        label.name.lower(): label
        for label in Label.objects.filter(project_id=project.id, deleted_at__isnull=True)
    }

    issue_type_ids = ProjectIssueType.objects.filter(
        project_id=project.id,
        deleted_at__isnull=True,
    ).values_list("issue_type_id", flat=True)
    types_by_name = {
        issue_type.name.lower(): issue_type
        for issue_type in IssueType.objects.filter(id__in=issue_type_ids, deleted_at__isnull=True)
    }

    members_by_email = {
        (member.member.email or "").strip().lower(): member.member
        for member in ProjectMember.objects.filter(
            project_id=project.id,
            is_active=True,
            deleted_at__isnull=True,
        ).select_related("member")
        if member.member and member.member.email
    }
    members_by_name = {
        (member.member.display_name or member.member.full_name or "").strip().lower(): member.member
        for member in ProjectMember.objects.filter(
            project_id=project.id,
            is_active=True,
            deleted_at__isnull=True,
        ).select_related("member")
        if member.member
        and (member.member.display_name or member.member.full_name)
    }
    # Fallback: workspace members (may not be project members yet)
    for wm in WorkspaceMember.objects.filter(
        workspace_id=project.workspace_id,
        is_active=True,
    ).select_related("member"):
        email = (wm.member.email or "").strip().lower()
        if email and email not in members_by_email:
            members_by_email[email] = wm.member
        display = (wm.member.display_name or wm.member.full_name or "").strip().lower()
        if display and display not in members_by_name:
            members_by_name[display] = wm.member

    type_properties_by_type: dict = {}
    for issue_type in types_by_name.values():
        props = {
            prop.title.lower(): prop
            for prop in issue_type.properties.filter(deleted_at__isnull=True, is_active=True)
        }
        type_properties_by_type[str(issue_type.id)] = props

    prepared: list[dict] = []
    seen_keys: set[str] = set()

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if not name:
            warnings.append(f"Row {index + 1}: skipped work item without name")
            continue

        external_key = str(row.get("external_key", "")).strip() or f"ROW-{index + 1}"
        if external_key.lower() in seen_keys:
            warnings.append(f'Row {index + 1}: duplicate external_key "{external_key}", using ROW-{index + 1}')
            external_key = f"ROW-{index + 1}"
        seen_keys.add(external_key.lower())

        state_name = str(row.get("state", "")).strip().lower()
        state = states_by_name.get(state_name) if state_name else default_state
        if state_name and state is None:
            warnings.append(f'Row {index + 1}: unknown state "{row.get("state")}", using default')
            state = default_state
        if state is None:
            raise ValueError({"error": "Project has no states to attach work items to."})

        priority = str(row.get("priority", "none") or "none").strip().lower()
        if priority not in ALLOWED_PRIORITIES:
            priority = "none"

        issue_type_name = str(row.get("issue_type", "")).strip().lower()
        issue_type = types_by_name.get(issue_type_name) if issue_type_name else None
        if issue_type_name and issue_type is None:
            warnings.append(f'Row {index + 1}: unknown issue type "{row.get("issue_type")}", left empty')

        label_names = _coerce_list(row.get("labels"))
        label_ids = []
        for label_name in label_names:
            label = labels_by_name.get(str(label_name).strip().lower())
            if label:
                label_ids.append(label.id)
            else:
                warnings.append(f'Row {index + 1}: unknown label "{label_name}", skipped')

        assignee_emails = _coerce_list(row.get("assignee_emails"))
        assignee_names = _coerce_list(row.get("assignee_names") or row.get("assignees"))
        assignee_ids = []
        for email in assignee_emails:
            normalized_email = str(email).strip().lower()
            if not normalized_email:
                continue
            if "@" not in normalized_email:
                assignee_names.append(email)
                continue
            user_obj = members_by_email.get(normalized_email)
            if user_obj:
                assignee_ids.append(user_obj.id)
            else:
                warnings.append(
                    f'Row {index + 1}: assignee "{email}" not found in workspace; '
                    "work item left unassigned for that email"
                )
        for name_value in assignee_names:
            normalized_name = str(name_value).strip().lower()
            if not normalized_name:
                continue
            if "@" in normalized_name:
                continue
            user_obj = members_by_name.get(normalized_name)
            if user_obj and user_obj.id not in assignee_ids:
                assignee_ids.append(user_obj.id)
            elif user_obj is None:
                warnings.append(
                    f'Row {index + 1}: assignee "{name_value}" not found by name; '
                    "work item left unassigned for that person"
                )

        description_html = _normalize_description_html(row.get("description_html") or row.get("description"))
        custom_properties = _coerce_dict(row.get("custom_properties"))

        start_date = row.get("start_date") or None
        target_date = row.get("target_date") or None
        if start_date == "":
            start_date = None
        if target_date == "":
            target_date = None

        raw_duration = row.get("duration")
        duration = normalize_work_item_duration(raw_duration)
        if raw_duration not in [None, ""] and duration is None:
            warnings.append(f'Row {index + 1}: invalid duration "{raw_duration}", derived from the dates instead')

        # Run the same reconciliation the work item API runs on create, so an imported item keeps
        # duration, start date and target date consistent with one another.
        duration_payload = {"start_date": start_date, "target_date": target_date}
        if duration is not None:
            duration_payload["duration"] = duration
        derived = reconcile_work_item_duration(None, duration_payload)
        duration = derived.get("duration", duration)
        if "start_date" in derived:
            start_date = to_work_item_date(derived["start_date"])
        if "target_date" in derived:
            target_date = to_work_item_date(derived["target_date"])

        is_draft = row.get("is_draft")
        if isinstance(is_draft, str):
            is_draft = is_draft.strip().lower() in {"1", "true", "yes", "on"}
        else:
            is_draft = bool(is_draft)

        prepared.append(
            {
                "external_key": external_key,
                "name": name[:255],
                "description_html": description_html,
                "description_stripped": strip_tags(description_html)[:3000],
                "state": state,
                "priority": priority,
                "start_date": start_date,
                "target_date": target_date,
                "duration": duration,
                "is_draft": is_draft,
                "parent_external_key": str(row.get("parent_external_key", "") or "").strip(),
                "issue_type": issue_type,
                "label_ids": label_ids,
                "assignee_ids": assignee_ids,
                "custom_properties": custom_properties,
            }
        )

    if not prepared:
        return {"created_work_items": 0, "warnings": warnings}

    last_id = IssueSequence.objects.filter(project=project).aggregate(largest=Max("sequence"))["largest"]
    next_sequence = 1 if last_id is None else int(last_id) + 1

    largest_sort = (
        Issue.objects.filter(project=project, deleted_at__isnull=True).aggregate(largest=Max("sort_order"))["largest"]
    )
    next_sort = 65535 if largest_sort is None else float(largest_sort) + 10000

    key_to_issue: dict[str, Issue] = {}

    with transaction.atomic():
        issues_to_create: list[Issue] = []
        for item in prepared:
            issues_to_create.append(
                Issue(
                    project=project,
                    workspace=project.workspace,
                    name=item["name"],
                    description_html=item["description_html"],
                    description_stripped=item["description_stripped"],
                    state=item["state"],
                    priority=item["priority"],
                    start_date=item["start_date"],
                    target_date=item["target_date"],
                    duration=item["duration"],
                    is_draft=item["is_draft"],
                    type=item["issue_type"],
                    sequence_id=next_sequence,
                    sort_order=next_sort,
                    created_by=user,
                )
            )
            next_sequence += 1
            next_sort += 10000

        created_issues = Issue.objects.bulk_create(issues_to_create, batch_size=200)
        for item, issue in zip(prepared, created_issues):
            key_to_issue[item["external_key"].lower()] = issue

        IssueSequence.objects.bulk_create(
            [
                IssueSequence(
                    issue=issue,
                    sequence=issue.sequence_id,
                    project=project,
                    workspace=project.workspace,
                )
                for issue in created_issues
            ],
            batch_size=200,
        )

        IssueActivity.objects.bulk_create(
            [
                IssueActivity(
                    issue=issue,
                    actor=user,
                    project=project,
                    workspace=project.workspace,
                    comment="created the issue",
                    verb="created",
                    created_by=user,
                )
                for issue in created_issues
            ],
            batch_size=200,
        )

        # Pass 2: parent links
        parent_updates = []
        for item, issue in zip(prepared, created_issues):
            parent_key = item["parent_external_key"]
            if not parent_key:
                continue
            parent = key_to_issue.get(parent_key.lower())
            if parent is None:
                warnings.append(
                    f'Work item "{item["external_key"]}": parent "{parent_key}" not found in file, skipped'
                )
                continue
            if parent.id == issue.id:
                continue
            issue.parent = parent
            parent_updates.append(issue)
        if parent_updates:
            Issue.objects.bulk_update(parent_updates, ["parent"], batch_size=200)

        label_rows = []
        assignee_rows = []
        property_rows = []

        for item, issue in zip(prepared, created_issues):
            for label_id in item["label_ids"]:
                label_rows.append(
                    IssueLabel(
                        issue=issue,
                        label_id=label_id,
                        project=project,
                        workspace=project.workspace,
                    )
                )
            for assignee_id in item["assignee_ids"]:
                assignee_rows.append(
                    IssueAssignee(
                        issue=issue,
                        assignee_id=assignee_id,
                        project=project,
                        workspace=project.workspace,
                    )
                )

            if item["issue_type"] and item["custom_properties"]:
                props = type_properties_by_type.get(str(item["issue_type"].id), {})
                for title, raw_value in item["custom_properties"].items():
                    prop = props.get(str(title).strip().lower())
                    if not prop:
                        warnings.append(
                            f'Work item "{item["external_key"]}": unknown custom property "{title}", skipped'
                        )
                        continue
                    try:
                        cleaned_value = validate_property_value(
                            property_type=prop.property_type,
                            value=raw_value,
                            select_mode=prop.select_mode or "single",
                            options=prop.options or [],
                        )
                    except ValueError as exc:
                        warnings.append(
                            f'Work item "{item["external_key"]}": property "{title}" invalid ({exc}), skipped'
                        )
                        continue
                    property_rows.append(
                        IssuePropertyValue(
                            issue=issue,
                            property=prop,
                            value=cleaned_value,
                            project=project,
                            workspace=project.workspace,
                        )
                    )

        if label_rows:
            IssueLabel.objects.bulk_create(label_rows, batch_size=500, ignore_conflicts=True)
        if assignee_rows:
            IssueAssignee.objects.bulk_create(assignee_rows, batch_size=500, ignore_conflicts=True)
        if property_rows:
            IssuePropertyValue.objects.bulk_create(property_rows, batch_size=500, ignore_conflicts=True)

    return {"created_work_items": len(created_issues), "warnings": warnings}
