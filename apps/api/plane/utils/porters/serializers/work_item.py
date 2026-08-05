from plane.db.models import Issue

MAX_WORK_ITEMS_EXPORT = 500


def serialize_work_item_export_rows(project, *, limit: int = MAX_WORK_ITEMS_EXPORT) -> list[dict]:
    """Serialize project issues into CSV-friendly rows."""
    issues = (
        Issue.objects.filter(
            project_id=project.id,
            deleted_at__isnull=True,
            archived_at__isnull=True,
        )
        .select_related("state", "type", "parent")
        .prefetch_related(
            "assignees",
            "label_issue__label",
            "type_property_values__property",
        )
        .order_by("sequence_id")[:limit]
    )

    rows: list[dict] = []
    for issue in issues:
        external_key = f"{project.identifier}-{issue.sequence_id}"
        parent_key = ""
        if issue.parent_id and issue.parent and issue.parent.deleted_at is None:
            parent_key = f"{project.identifier}-{issue.parent.sequence_id}"

        labels = [
            issue_label.label.name
            for issue_label in issue.label_issue.all()
            if issue_label.deleted_at is None and issue_label.label and issue_label.label.deleted_at is None
        ]
        assignee_emails = [
            user.email for user in issue.assignees.all() if getattr(user, "is_active", True) and user.email
        ]

        custom_properties: dict = {}
        for prop_value in issue.type_property_values.all():
            if prop_value.deleted_at is not None:
                continue
            prop = prop_value.property
            if not prop or prop.deleted_at is not None:
                continue
            custom_properties[prop.title] = prop_value.value

        rows.append(
            {
                "external_key": external_key,
                "name": issue.name or "",
                "description_html": issue.description_html or "",
                "state": issue.state.name if issue.state else "",
                "priority": issue.priority or "none",
                "start_date": issue.start_date.isoformat() if issue.start_date else "",
                "target_date": issue.target_date.isoformat() if issue.target_date else "",
                "is_draft": bool(issue.is_draft),
                "parent_external_key": parent_key,
                "issue_type": issue.type.name if issue.type else "",
                "labels": labels,
                "assignee_emails": assignee_emails,
                "custom_properties": custom_properties,
            }
        )

    return rows
