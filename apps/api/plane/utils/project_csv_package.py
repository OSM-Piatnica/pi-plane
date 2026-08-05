from plane.utils.project_template_payload import ALLOWED_PAYLOAD_KEYS

ROW_TYPE_PROJECT = "project"
ROW_TYPE_WORK_ITEM = "work_item"

WORK_ITEM_PAYLOAD_KEYS = frozenset(
    {
        "external_key",
        "name",
        "description_html",
        "state",
        "priority",
        "start_date",
        "target_date",
        "is_draft",
        "parent_external_key",
        "issue_type",
        "labels",
        "assignee_emails",
        "custom_properties",
    }
)


def build_full_project_export_rows(project_payload: dict, work_item_rows: list[dict]) -> list[dict]:
    return [
        {"row_type": ROW_TYPE_PROJECT, **project_payload},
        *[{"row_type": ROW_TYPE_WORK_ITEM, **row} for row in work_item_rows],
    ]


def _strip_row_type(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "row_type"}


def _project_payload_from_row(row: dict) -> dict:
    cleaned = _strip_row_type(row)
    return {key: value for key, value in cleaned.items() if key in ALLOWED_PAYLOAD_KEYS}


def _work_item_payload_from_row(row: dict) -> dict:
    cleaned = _strip_row_type(row)
    return {key: value for key, value in cleaned.items() if key in WORK_ITEM_PAYLOAD_KEYS}


def split_import_rows(rows: list[dict]) -> tuple[list[dict], list[dict] | None]:
    """Split CSV rows into project payloads and optional work-item payloads."""
    if not rows:
        return [], None

    row_types = {str(row.get("row_type") or "").strip().lower() for row in rows}
    if ROW_TYPE_PROJECT not in row_types and ROW_TYPE_WORK_ITEM not in row_types:
        return rows, None

    project_rows: list[dict] = []
    work_item_rows: list[dict] = []
    for row in rows:
        row_type = str(row.get("row_type") or "").strip().lower()
        if row_type == ROW_TYPE_WORK_ITEM:
            work_item_rows.append(_work_item_payload_from_row(row))
        elif row_type == ROW_TYPE_PROJECT:
            project_rows.append(_project_payload_from_row(row))

    return project_rows, work_item_rows if work_item_rows else None
