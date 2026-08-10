from plane.utils.project_csv_package import build_full_project_export_rows, split_import_rows


def test_build_and_split_full_project_csv_rows():
    project = {"name": "Helpdesk", "identifier": "ITHELP", "description": "Demo"}
    work_items = [
        {"external_key": "ITHELP-1", "name": "Broken laptop", "state": "Todo", "priority": "high"},
        {"external_key": "ITHELP-2", "name": "VPN issue", "state": "Todo", "priority": "medium"},
    ]

    rows = build_full_project_export_rows(project, work_items)
    assert rows[0]["row_type"] == "project"
    assert rows[1]["row_type"] == "work_item"
    assert len(rows) == 3

    project_rows, wi_rows = split_import_rows(rows)
    assert len(project_rows) == 1
    assert project_rows[0]["identifier"] == "ITHELP"
    assert "row_type" not in project_rows[0]
    assert "external_key" not in project_rows[0]
    assert wi_rows is not None
    assert len(wi_rows) == 2
    assert wi_rows[0]["external_key"] == "ITHELP-1"
    assert "identifier" not in wi_rows[0]


def test_split_legacy_config_only_csv():
    rows = [{"name": "Only Config", "identifier": "CFG"}]
    project_rows, wi_rows = split_import_rows(rows)
    assert project_rows == rows
    assert wi_rows is None
