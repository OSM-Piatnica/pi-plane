from plane.db.models import (
    IssueType,
    IssueTypeProperty,
    Label,
    Project,
    ProjectIssueType,
    State,
)


def _serialize_custom_properties(issue_type: IssueType) -> list[dict]:
    rows = []
    for prop in IssueTypeProperty.objects.filter(
        issue_type=issue_type,
        deleted_at__isnull=True,
    ).order_by("sort_order"):
        row = {
            "title": prop.title,
            "description": prop.description or "",
            "is_mandatory": prop.is_mandatory,
            "is_active": prop.is_active,
            "property_type": prop.property_type,
        }
        if prop.property_type == "dropdown":
            row["options"] = prop.options or []
            row["select_mode"] = prop.select_mode or "single"
            if prop.default_value:
                row["default_option"] = prop.default_value
        rows.append(row)
    return rows


def serialize_project_export_payload(project: Project) -> dict:
    payload: dict = {
        "name": project.name,
        "identifier": project.identifier,
        "description": project.description or "",
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "target_date": project.target_date.isoformat() if project.target_date else None,
        "network": project.network,
        "cycle_view": project.cycle_view,
        "module_view": project.module_view,
        "issue_views_view": project.issue_views_view,
        "page_view": project.page_view,
        "intake_view": project.intake_view,
        "is_time_tracking_enabled": project.is_time_tracking_enabled,
        "is_issue_type_enabled": project.is_issue_type_enabled,
        "guest_view_all_features": project.guest_view_all_features,
    }

    if project.project_lead_id:
        payload["project_lead"] = str(project.project_lead_id)
    if project.default_assignee_id:
        payload["default_assignee"] = str(project.default_assignee_id)

    states = State.objects.filter(project_id=project.id, deleted_at__isnull=True, is_triage=False).order_by("sequence")
    payload["state_templates"] = [
        {
            "name": state.name,
            "group": state.group,
            "color": state.color,
            "default": state.default,
        }
        for state in states
    ]

    labels = Label.objects.filter(project_id=project.id, deleted_at__isnull=True).order_by("sort_order")
    payload["label_templates"] = [{"name": label.name, "color": label.color} for label in labels]

    if not project.is_issue_type_enabled:
        payload["epic_enabled"] = False
        return payload

    links = (
        ProjectIssueType.objects.filter(project_id=project.id, deleted_at__isnull=True)
        .select_related("issue_type")
        .order_by("level")
    )
    epic_enabled = False
    additional_types: list[dict] = []

    for link in links:
        issue_type = link.issue_type
        if not issue_type or issue_type.deleted_at is not None:
            continue
        if issue_type.name == "Task" and not issue_type.is_epic:
            props = _serialize_custom_properties(issue_type)
            if props:
                payload["task_custom_properties"] = props
            continue
        if issue_type.name == "Epic" and issue_type.is_epic:
            epic_enabled = True
            props = _serialize_custom_properties(issue_type)
            if props:
                payload["epic_custom_properties"] = props
            continue
        additional_types.append(
            {
                "name": issue_type.name,
                "description": issue_type.description or "",
                "custom_properties": _serialize_custom_properties(issue_type),
            }
        )

    payload["epic_enabled"] = epic_enabled
    if additional_types:
        payload["additional_work_item_types"] = additional_types

    return payload
