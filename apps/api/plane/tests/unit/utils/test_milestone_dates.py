# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A milestone is one day: `apply_milestone_dates` keeps its start equal to its finish; date shifting keeps it so."""

from datetime import date
from types import SimpleNamespace

import pytest

from plane.db.models import IssueTypeKind
from plane.utils.issue_reschedule import _move_to, follow
from plane.utils.milestone_dates import apply_milestone_dates, is_milestone_type

MILESTONE = SimpleNamespace(id="m", kind=IssueTypeKind.MILESTONE)
STANDARD = SimpleNamespace(id="s", kind=IssueTypeKind.STANDARD)
WEEKEND = (0, 6)  # Sunday and Saturday


def _issue(start=None, finish=None, type_id="m"):
    return SimpleNamespace(start_date=start, finish_date=finish, type_id=type_id)


@pytest.mark.unit
class TestApplyMilestoneDates:
    def test_only_a_milestone_is_touched(self):
        payload = {"start_date": date(2026, 3, 2), "finish_date": date(2026, 3, 6), "duration": 5}
        apply_milestone_dates(None, payload, STANDARD)
        assert payload == {"start_date": date(2026, 3, 2), "finish_date": date(2026, 3, 6), "duration": 5}
        apply_milestone_dates(None, payload, None)
        assert payload["finish_date"] == date(2026, 3, 6)

    def test_the_start_follows_a_finish_sent_alone(self):
        payload = {"finish_date": date(2026, 3, 6)}
        apply_milestone_dates(_issue(date(2026, 3, 1), date(2026, 3, 1)), payload, MILESTONE)
        assert payload == {"start_date": date(2026, 3, 6), "finish_date": date(2026, 3, 6)}

    def test_the_finish_follows_a_start_sent_alone(self):
        payload = {"start_date": date(2026, 3, 2)}
        apply_milestone_dates(None, payload, MILESTONE)
        assert payload == {"start_date": date(2026, 3, 2), "finish_date": date(2026, 3, 2)}

    def test_the_finish_decides_when_both_are_sent(self):
        payload = {"start_date": date(2026, 3, 2), "finish_date": date(2026, 3, 6)}
        apply_milestone_dates(None, payload, MILESTONE)
        assert payload == {"start_date": date(2026, 3, 6), "finish_date": date(2026, 3, 6)}

    def test_a_cleared_finish_keeps_a_start_that_was_sent(self):
        payload = {"start_date": date(2026, 3, 2), "finish_date": None}
        apply_milestone_dates(None, payload, MILESTONE)
        assert payload == {"start_date": date(2026, 3, 2), "finish_date": date(2026, 3, 2)}

    def test_clearing_the_finish_clears_the_milestone(self):
        payload = {"finish_date": None}
        apply_milestone_dates(_issue(date(2026, 3, 2), date(2026, 3, 2)), payload, MILESTONE)
        assert payload == {"start_date": None, "finish_date": None}

    def test_a_duration_that_is_sent_is_dropped(self):
        payload = {"duration": 5}
        apply_milestone_dates(_issue(date(2026, 3, 2), date(2026, 3, 2)), payload, MILESTONE)
        assert payload == {}

    def test_the_due_date_is_never_touched(self):
        payload = {"finish_date": date(2026, 3, 6), "target_date": date(2026, 3, 4)}
        apply_milestone_dates(None, payload, MILESTONE)
        assert payload["target_date"] == date(2026, 3, 4)
        payload = {"target_date": date(2026, 3, 4)}
        apply_milestone_dates(_issue(date(2026, 3, 2), date(2026, 3, 2)), payload, MILESTONE)
        assert payload == {"target_date": date(2026, 3, 4)}

    def test_a_work_item_that_becomes_a_milestone_collapses_onto_its_finish(self):
        payload = {"type": MILESTONE}
        apply_milestone_dates(_issue(date(2026, 3, 2), date(2026, 3, 6), type_id="s"), payload, MILESTONE)
        assert payload["start_date"] == payload["finish_date"] == date(2026, 3, 6)

    def test_a_work_item_with_only_a_start_collapses_onto_it(self):
        payload = {"type": MILESTONE}
        apply_milestone_dates(_issue(date(2026, 3, 2), None, type_id="s"), payload, MILESTONE)
        assert payload["start_date"] == payload["finish_date"] == date(2026, 3, 2)

    def test_an_unchanged_milestone_without_dates_in_the_request_is_left_alone(self):
        payload = {"name": "Go-live"}
        apply_milestone_dates(_issue(date(2026, 3, 2), date(2026, 3, 6)), payload, MILESTONE)
        assert payload == {"name": "Go-live"}

    def test_is_milestone_type(self):
        assert is_milestone_type(MILESTONE)
        assert not is_milestone_type(STANDARD)
        assert not is_milestone_type(None)


@pytest.mark.unit
class TestDateShiftingKeepsAMilestoneAtOneDay:
    @pytest.mark.parametrize("day", [date(2026, 3, 4), date(2026, 3, 7)])  # a Wednesday and a Saturday
    @pytest.mark.parametrize("offset", [-3, -1, 1, 2, 5])
    def test_following_a_parent(self, day, offset):
        start, finish = follow({"start_date": day, "finish_date": day}, offset, WEEKEND)
        assert start == finish

    @pytest.mark.parametrize("field_name", ["start_date", "finish_date"])
    @pytest.mark.parametrize("earliest", [date(2026, 3, 9), date(2026, 3, 13)])  # a Monday and a Friday
    def test_moving_after_a_predecessor(self, field_name, earliest):
        start, finish = _move_to(
            {"start_date": date(2026, 3, 7), "finish_date": date(2026, 3, 7)}, field_name, earliest, WEEKEND
        )
        assert start == finish == earliest
