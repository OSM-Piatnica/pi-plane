# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RACI warnings of a project: missing roles, departments nobody hears for, and dependency gaps."""

from datetime import date

import pytest

from plane.utils.raci_warnings import (
    INACTIVE,
    MILESTONE_WITHOUT_APPROVER,
    NO_MEMBERS,
    NO_PREDECESSOR,
    NO_PROJECT_MEMBERS,
    NO_RESPONSIBLE,
    NO_SUCCESSOR,
    department_warnings,
    item_warnings,
    predecessor_edges,
)


def item(id, parent_id=None, kind=None, start=None, finish=None, target=None):
    return {
        "id": id,
        "parent_id": parent_id,
        "kind": kind,
        "start_date": start,
        "finish_date": finish,
        "target_date": target,
    }


@pytest.mark.unit
class TestEdges:
    def test_blocked_by_names_the_predecessor_second(self):
        assert predecessor_edges([("b", "a", "blocked_by")]) == [("a", "b")]

    def test_other_timeline_types_name_it_first_and_the_rest_is_ignored(self):
        relations = [("a", "b", "start_before"), ("a", "c", "finish_before"), ("a", "d", "relates_to")]

        assert predecessor_edges(relations) == [("a", "b"), ("a", "c")]


@pytest.mark.unit
class TestRoleWarnings:
    def test_work_item_without_responsible_is_listed(self):
        found = item_warnings([item("a"), item("b")], {"a": {"responsible"}, "b": {"consulted"}}, [])

        assert found[NO_RESPONSIBLE] == ["b"]

    def test_sub_items_are_checked_for_roles_too(self):
        found = item_warnings([item("a"), item("s", parent_id="a")], {"a": {"responsible"}}, [])

        assert found[NO_RESPONSIBLE] == ["s"]

    def test_milestone_without_approver(self):
        items = [item("m", kind="milestone"), item("n", kind="milestone"), item("x")]
        roles = {"m": {"responsible"}, "n": {"approver", "responsible"}, "x": {"responsible"}}

        assert item_warnings(items, roles, [])[MILESTONE_WITHOUT_APPROVER] == ["m"]


@pytest.mark.unit
class TestDependencyWarnings:
    def test_nothing_without_any_relation(self):
        found = item_warnings([item("a"), item("b")], {}, [])

        assert found[NO_PREDECESSOR] == [] and found[NO_SUCCESSOR] == []

    def test_project_start_and_end_are_not_warned_about(self):
        items = [
            item("start", start=date(2026, 1, 5), finish=date(2026, 1, 9)),
            item("mid", start=date(2026, 1, 12), finish=date(2026, 1, 16)),
            item("end", start=date(2026, 1, 19), finish=date(2026, 1, 23)),
            item("loose", start=date(2026, 1, 12), finish=date(2026, 1, 14)),
        ]
        edges = [("start", "mid"), ("mid", "end")]

        found = item_warnings(items, {}, edges)

        assert found[NO_PREDECESSOR] == ["loose"]
        assert found[NO_SUCCESSOR] == ["loose"]

    def test_a_due_date_is_reason_enough_to_end_a_chain(self):
        items = [item("a", start=date(2026, 1, 5)), item("b", target=date(2026, 2, 1)), item("c")]

        found = item_warnings(items, {}, [("a", "b")])

        assert "b" not in found[NO_SUCCESSOR]
        assert found[NO_SUCCESSOR] == ["c"]

    def test_sub_items_are_left_out_of_dependency_checks(self):
        items = [item("a", start=date(2026, 1, 5)), item("b"), item("s", parent_id="a")]

        found = item_warnings(items, {}, [("a", "b")])

        assert "s" not in found[NO_PREDECESSOR] and "s" not in found[NO_SUCCESSOR]

    def test_predecessors_outside_the_list_count(self):
        found = item_warnings(
            [item("b", start=date(2026, 3, 1)), item("c", start=date(2026, 1, 1))], {}, [("elsewhere", "b")]
        )

        assert found[NO_PREDECESSOR] == []


@pytest.mark.unit
class TestDepartmentWarnings:
    def test_reasons(self):
        departments = [
            {"group_id": "off", "is_active": False, "member_count": 3, "project_member_count": 3},
            {"group_id": "empty", "is_active": True, "member_count": 0, "project_member_count": 0},
            {"group_id": "outside", "is_active": True, "member_count": 2, "project_member_count": 0},
            {"group_id": "fine", "is_active": True, "member_count": 2, "project_member_count": 1},
        ]

        found = {entry["group_id"]: entry["reason"] for entry in department_warnings(departments)}

        assert found == {"off": INACTIVE, "empty": NO_MEMBERS, "outside": NO_PROJECT_MEMBERS}
