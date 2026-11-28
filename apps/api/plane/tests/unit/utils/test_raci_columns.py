# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The RACI column of work item files: reading and writing "O:RM;K:PR;Z:ZA" (no database needed)."""

from types import SimpleNamespace
from unittest import mock

import pytest

from plane.utils.community_work_item_import import map_community_export_rows
from plane.utils.porters.exporter import DataExporter
from plane.utils.porters.importer import DataImporter
from plane.utils.porters.serializers.issue import IssueExportSerializer
from plane.utils.raci_columns import (
    format_raci_cell,
    letters_for_language,
    parse_raci_cell,
    parse_raci_entry,
)


@pytest.mark.unit
class TestReadingACell:
    def test_polish_letters(self):
        entries, unreadable = parse_raci_cell("O:RM;K:PR;Z:ZA;I:QA")

        assert entries == [("responsible", "RM"), ("consulted", "PR"), ("approver", "ZA"), ("informed", "QA")]
        assert unreadable == []

    def test_english_letters_mean_the_same_roles(self):
        entries, _ = parse_raci_cell("R:RM;C:PR;A:ZA;I:QA")

        assert entries == [("responsible", "RM"), ("consulted", "PR"), ("approver", "ZA"), ("informed", "QA")]

    def test_case_spaces_and_line_breaks_do_not_matter(self):
        entries, _ = parse_raci_cell(" o : rm ;\nk:Marketing i sprzedaż ; ")

        assert entries == [("responsible", "rm"), ("consulted", "Marketing i sprzedaż")]

    def test_two_responsible_departments(self):
        entries, _ = parse_raci_cell("O:RM;O:PR")

        assert entries == [("responsible", "RM"), ("responsible", "PR")]

    def test_an_escaped_semicolon_stays_in_the_name(self):
        entries, _ = parse_raci_cell("O:Dział A\\; B;K:PR")

        assert entries == [("responsible", "Dział A; B"), ("consulted", "PR")]

    def test_entries_that_are_not_a_letter_and_a_department_are_reported(self):
        entries, unreadable = parse_raci_cell("X:RM;RM;O:;O:PR")

        assert entries == [("responsible", "PR")]
        assert unreadable == ["X:RM", "RM", "O:"]

    def test_an_empty_cell_and_a_list(self):
        assert parse_raci_cell(None) == ([], [])
        assert parse_raci_cell("") == ([], [])
        assert parse_raci_cell(["O:RM", "Z:ZA"]) == ([("responsible", "RM"), ("approver", "ZA")], [])

    def test_a_prototype_label(self):
        assert parse_raci_entry("O:RM") == ("responsible", "RM")
        assert parse_raci_entry("Z:ZA") == ("approver", "ZA")
        assert parse_raci_entry("pilne") is None
        assert parse_raci_entry("Q:RM") is None


@pytest.mark.unit
class TestWritingACell:
    entries = [
        ("informed", "QA"),
        ("responsible", "RM"),
        ("approver", "ZA"),
        ("responsible", "PR"),
        ("consulted", "KS"),
    ]

    def test_polish_letters_in_role_order(self):
        assert format_raci_cell(self.entries, "pl") == "O:RM;O:PR;Z:ZA;K:KS;I:QA"

    def test_english_letters_in_role_order(self):
        assert format_raci_cell(self.entries, "en") == "R:RM;R:PR;A:ZA;C:KS;I:QA"

    def test_a_semicolon_in_a_name_is_escaped_and_read_back(self):
        cell = format_raci_cell([("responsible", "Dział A; B")], "pl")

        assert cell == "O:Dział A\\; B"
        assert parse_raci_cell(cell)[0] == [("responsible", "Dział A; B")]

    def test_nothing_gives_an_empty_cell(self):
        assert format_raci_cell([], "pl") == ""

    def test_the_language_picks_the_letters(self):
        assert letters_for_language("pl") == "pl"
        assert letters_for_language("pl-x-podlaski") == "pl"
        assert letters_for_language("en") == "en"
        assert letters_for_language("de") == "en"
        assert letters_for_language(None) == "en"


class _Prefetched(list):
    def all(self):
        return self


def _department(name, code, sort_order):
    return SimpleNamespace(name=name, code=code, sort_order=sort_order, kind="department", deleted_at=None)


def _demo_issue():
    roles = [
        ("informed", _department("Jakość", "QA", 3)),
        ("responsible", _department("Marketing", "RM", 1)),
        ("approver", _department("Zarząd", "", 2)),
    ]
    return SimpleNamespace(
        project=SimpleNamespace(identifier="DEMO", name="Demo", timezone="UTC"),
        project_id="demo",
        sequence_id=3,
        name="Projekt etykiety",
        state=SimpleNamespace(name="Todo"),
        issue_raci=_Prefetched(SimpleNamespace(role=role, group=group, deleted_at=None) for role, group in roles),
    )


@pytest.mark.unit
@pytest.mark.parametrize("file_format", ["csv", "xlsx", "json"])
@pytest.mark.parametrize(("letters", "cell"), [("pl", "O:RM;Z:Zarząd;I:QA"), ("en", "R:RM;A:Zarząd;I:QA")])
def test_the_raci_column_of_an_export_is_the_one_the_import_reads(file_format, letters, cell):
    with mock.patch("plane.utils.porters.serializers.issue.project_raci_enabled", return_value=True):
        exporter = DataExporter(
            IssueExportSerializer,
            format_type=file_format,
            export_fields=["identifier", "name", "state_name", "raci"],
            context={"raci_letters": letters},
        )
        _, content = exporter.export("export", [_demo_issue()])
    if isinstance(content, str):
        content = content.encode("utf-8")
    if file_format == "csv":
        assert b"RACI" in content.splitlines()[0]

    rows = DataImporter(format_type=file_format).decode(content)
    mapped = map_community_export_rows(rows)

    assert mapped[0]["raci"] == cell


@pytest.mark.unit
def test_an_export_leaves_the_column_empty_where_raci_is_off():
    with mock.patch("plane.utils.porters.serializers.issue.project_raci_enabled", return_value=False):
        data = IssueExportSerializer([_demo_issue()], many=True, export_fields=["identifier", "raci"]).data

    assert data[0]["raci"] == ""
