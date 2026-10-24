# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date

import pytest

from plane.utils.issue_hierarchy import IssueTree, date_rollup


def row(id, parent_id=None, start=None, end=None):
    return {
        "id": id,
        "parent_id": parent_id,
        "start_date": date.fromisoformat(start) if start else None,
        "target_date": date.fromisoformat(end) if end else None,
    }


@pytest.mark.unit
class TestIssueTree:
    def test_children_and_descendants_at_any_depth(self):
        tree = IssueTree([row("a"), row("b", "a"), row("c", "b"), row("d", "a"), row("x")])
        assert sorted(tree.children("a")) == ["b", "d"]
        assert sorted(tree.descendants("a")) == ["b", "c", "d"]
        assert tree.descendants("x") == []

    def test_a_parent_that_is_not_among_the_rows_makes_its_children_roots(self):
        tree = IssueTree([row("b", "archived")])
        assert tree.children("archived") == []
        assert "b" in tree and "archived" not in tree

    def test_a_parent_cycle_does_not_loop(self):
        tree = IssueTree([row("a", "c"), row("b", "a"), row("c", "b"), row("self", "self")])
        assert sorted(tree.descendants("a")) == ["b", "c"]
        assert tree.descendants("self") == []


@pytest.mark.unit
class TestDateRollup:
    def test_none_without_descendants(self):
        assert date_rollup(IssueTree([row("a", start="2026-01-01", end="2026-01-31")]), "a") is None

    def test_earliest_start_to_latest_end_over_all_levels(self):
        tree = IssueTree(
            [
                row("a", start="2026-02-01", end="2026-02-10"),
                row("b", "a", start="2026-02-05", end="2026-02-20"),
                row("c", "b", start="2026-01-15", end="2026-01-31"),
                row("d", "a"),
            ]
        )
        assert date_rollup(tree, "a") == {
            "start_date": date(2026, 1, 15),
            "target_date": date(2026, 2, 20),
            "children_count": 2,
            "descendants_count": 3,
        }

    def test_a_single_date_counts_as_one_day(self):
        tree = IssueTree([row("a"), row("b", "a", start="2026-03-04"), row("c", "a", end="2026-03-09")])
        rollup = date_rollup(tree, "a")
        assert (rollup["start_date"], rollup["target_date"]) == (date(2026, 3, 4), date(2026, 3, 9))

    def test_no_dates_below_gives_counts_only(self):
        tree = IssueTree([row("a"), row("b", "a")])
        assert date_rollup(tree, "a") == {
            "start_date": None,
            "target_date": None,
            "children_count": 1,
            "descendants_count": 1,
        }
