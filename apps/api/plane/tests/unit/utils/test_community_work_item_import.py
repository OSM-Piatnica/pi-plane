# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.utils.community_work_item_import import (
    is_community_work_item_export,
    map_community_export_rows,
)


def test_detects_community_export_headers():
    rows = [
        {
            "project_name": "Demo",
            "project_identifier": "DEM",
            "identifier": "DEM-1",
            "name": "Task",
            "state_name": "Todo",
            "priority": "high",
        }
    ]
    assert is_community_work_item_export(rows) is True


def test_rejects_full_project_work_item_rows():
    rows = [
        {
            "external_key": "WI-1",
            "name": "Task",
            "state": "Todo",
            "priority": "none",
        }
    ]
    assert is_community_work_item_export(rows) is False


def test_maps_community_columns_to_internal_rows():
    rows = [
        {
            "Project Name": "Demo",
            "identifier": "DEM-2",
            "name": "Child",
            "state_name": "In Progress",
            "priority": "medium",
            "parent": "DEM-1",
            "start_date": "2026-06-29",
            "due_date": "2026-07-01",
            "duration": 3,
            "assignees": ["Ada Lovelace", "bob@example.com"],
            "labels": ["bug"],
            "description": "Hello",
        }
    ]
    mapped = map_community_export_rows(rows)
    assert len(mapped) == 1
    assert mapped[0]["external_key"] == "DEM-2"
    assert mapped[0]["state"] == "In Progress"
    assert mapped[0]["parent_external_key"] == "DEM-1"
    assert mapped[0]["target_date"] == "2026-07-01"
    assert mapped[0]["duration"] == 3
    assert mapped[0]["assignee_names"] == ["Ada Lovelace"]
    assert mapped[0]["assignee_emails"] == ["bob@example.com"]


def test_maps_modules_cycles_subscribers_and_relations():
    rows = [
        {
            "identifier": "DEM-3",
            "name": "Full row",
            "state_name": "Todo",
            "modules": '["Kampania"]',
            "cycles": '["Sprint 1"]',
            "subscribers": '["watcher@example.com"]',
            "relations": '[{"type": "blocking", "issue": "DEM-1"}]',
            "estimate": "5",
        }
    ]
    mapped = map_community_export_rows(rows)

    assert mapped[0]["modules"] == '["Kampania"]'
    assert mapped[0]["cycles"] == '["Sprint 1"]'
    assert mapped[0]["subscriber_emails"] == ["watcher@example.com"]
    assert mapped[0]["relations"] == '[{"type": "blocking", "issue": "DEM-1"}]'
    assert mapped[0]["estimate"] == "5"


def test_unwraps_rows_saved_as_one_quoted_cell():
    from plane.utils.community_work_item_import import _unwrap_collapsed_rows
    from plane.utils.porters.formatters import CSVFormatter

    content = (
        'Project Name,Identifier,Name,Assignees,Is Draft\n"Demo,DEM-1,""11.02,26- Z -70"",""[""""a@x.pl""""]"",False"\n'
    )
    rows = _unwrap_collapsed_rows(CSVFormatter().decode(content))
    assert rows[0]["name"] == "11.02,26- Z -70"
    assert rows[0]["assignees"] == '["a@x.pl"]'  # the importer parses list strings
    assert rows[0]["project_name"] == "Demo"


def test_missing_name_column_error_lists_found_columns():
    import pytest

    from plane.utils.community_work_item_import import import_community_work_items_into_project

    with pytest.raises(ValueError) as exc:
        import_community_work_items_into_project(project=None, user=None, rows=[{"project_name": "x"}])
    assert "project_name" in exc.value.args[0]["error"]


def test_xlsx_with_wrong_stored_dimensions_reads_every_column():
    import io
    import re
    import zipfile

    from openpyxl import Workbook

    from plane.utils.porters.formatters import XLSXFormatter

    wb = Workbook()
    wb.active.append(["Project Name", "Name", "State Name"])
    wb.active.append(["Demo", "Task", "Todo"])
    wb.active.append([None, None, None])
    buffer = io.BytesIO()
    wb.save(buffer)

    # Rewrite the sheet so it claims to be one cell wide, as some converters do
    patched = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as src, zipfile.ZipFile(patched, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                data = re.sub(rb'<dimension ref="[^"]*"', b'<dimension ref="A1"', data)
            dst.writestr(item, data)

    rows = XLSXFormatter().decode(patched.getvalue())
    assert rows == [{"project_name": "Demo", "name": "Task", "state_name": "Todo"}]


def test_maps_the_cycle_period_columns():
    rows = [
        {
            "Identifier": "DEM-5",
            "Name": "Cycle period",
            "State Name": "Todo",
            "Cycles": '["Sprint 1"]',
            "Cycle Start Date": "2026-06-01",
            "Cycle End Date": "2026-06-14",
        }
    ]
    mapped = map_community_export_rows(rows)

    assert mapped[0]["cycles"] == '["Sprint 1"]'
    assert mapped[0]["cycle_start_date"] == "2026-06-01"
    assert mapped[0]["cycle_end_date"] == "2026-06-14"
