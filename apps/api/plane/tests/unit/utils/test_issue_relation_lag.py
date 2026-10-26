# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Lag and lead on the date rules, and the start-to-finish relation."""

from datetime import date

import pytest

from plane.utils.issue_relation_constraints import (
    TIMELINE_RELATION_TYPES,
    date_violation_error,
    is_status_transition_allowed,
    is_timeline_relation_satisfied,
)
from plane.utils.issue_relation_mapper import get_actual_relation, get_inverse_relation

D = date


def satisfied(relation_type, issue, related, lag=0):
    return is_timeline_relation_satisfied(
        relation_type,
        {"start_date": issue[0], "target_date": issue[1]},
        {"start_date": related[0], "target_date": related[1]},
        lag,
    )


@pytest.mark.unit
class TestFinishToStartLag:
    # the blocker is January 1-10
    blocker = (D(2026, 1, 1), D(2026, 1, 10))

    def test_no_lag_asks_for_the_day_after(self):
        assert satisfied("blocked_by", (D(2026, 1, 11), None), self.blocker) is True
        assert satisfied("blocked_by", (D(2026, 1, 10), None), self.blocker) is False

    def test_a_lag_asks_for_free_days_in_between(self):
        assert satisfied("blocked_by", (D(2026, 1, 12), None), self.blocker, lag=2) is False
        assert satisfied("blocked_by", (D(2026, 1, 13), None), self.blocker, lag=2) is True

    def test_a_lead_lets_them_overlap(self):
        assert satisfied("blocked_by", (D(2026, 1, 10), None), self.blocker, lag=-1) is True
        assert satisfied("blocked_by", (D(2026, 1, 9), None), self.blocker, lag=-1) is False

    def test_the_blocking_side_reads_the_same_lag(self):
        blocked = (D(2026, 1, 13), None)
        assert satisfied("blocking", self.blocker, blocked, lag=2) is True
        assert satisfied("blocking", self.blocker, (D(2026, 1, 12), None), lag=2) is False


@pytest.mark.unit
class TestStartAndFinishLag:
    def test_start_to_start(self):
        assert satisfied("start_before", (D(2026, 1, 1), None), (D(2026, 1, 3), None), lag=2) is True
        assert satisfied("start_before", (D(2026, 1, 1), None), (D(2026, 1, 2), None), lag=2) is False
        assert satisfied("start_after", (D(2026, 1, 3), None), (D(2026, 1, 1), None), lag=2) is True
        assert satisfied("start_after", (D(2026, 1, 2), None), (D(2026, 1, 1), None), lag=2) is False

    def test_finish_to_finish(self):
        assert satisfied("finish_before", (None, D(2026, 2, 1)), (None, D(2026, 2, 4)), lag=3) is True
        assert satisfied("finish_before", (None, D(2026, 2, 1)), (None, D(2026, 2, 3)), lag=3) is False
        assert satisfied("finish_after", (None, D(2026, 2, 4)), (None, D(2026, 2, 1)), lag=3) is True

    def test_a_missing_date_lifts_the_constraint(self):
        for relation_type in TIMELINE_RELATION_TYPES:
            assert satisfied(relation_type, (None, None), (D(2026, 1, 1), D(2026, 1, 2)), lag=5) is True


@pytest.mark.unit
class TestStartToFinish:
    def test_is_a_pair_stored_under_the_forward_name(self):
        assert get_inverse_relation("start_before_finish") == "finish_after_start"
        assert get_inverse_relation("finish_after_start") == "start_before_finish"
        assert get_actual_relation("finish_after_start") == "start_before_finish"
        assert {"start_before_finish", "finish_after_start"} <= TIMELINE_RELATION_TYPES

    def test_the_related_item_cannot_finish_before_this_one_starts(self):
        # this item starts January 10; the related one has to finish on or after that
        assert satisfied("start_before_finish", (D(2026, 1, 10), None), (None, D(2026, 1, 10))) is True
        assert satisfied("start_before_finish", (D(2026, 1, 10), None), (None, D(2026, 1, 9))) is False

    def test_the_reverse_side_reads_the_same_rule(self):
        # this item finishes January 9; the related one (the predecessor) started January 10: violated
        assert satisfied("finish_after_start", (None, D(2026, 1, 9)), (D(2026, 1, 10), None)) is False
        assert satisfied("finish_after_start", (None, D(2026, 1, 10)), (D(2026, 1, 10), None)) is True

    def test_lag_shifts_it(self):
        assert satisfied("start_before_finish", (D(2026, 1, 10), None), (None, D(2026, 1, 12)), lag=2) is True
        assert satisfied("start_before_finish", (D(2026, 1, 10), None), (None, D(2026, 1, 11)), lag=2) is False

    def test_completing_waits_for_the_other_item_to_start(self):
        assert is_status_transition_allowed("finish_after_start", "completed", "backlog") is False
        assert is_status_transition_allowed("finish_after_start", "completed", "unstarted") is False
        assert is_status_transition_allowed("finish_after_start", "completed", "started") is True
        assert is_status_transition_allowed("finish_after_start", "completed", "completed") is True
        assert is_status_transition_allowed("finish_after_start", "started", "backlog") is True
        assert is_status_transition_allowed("finish_after_start", "completed", "cancelled") is True
        assert is_status_transition_allowed("start_before_finish", "completed", "backlog") is True


@pytest.mark.unit
class TestErrorPayload:
    def test_carries_the_lag_so_the_web_app_can_say_so(self):
        error = date_violation_error("blocked_by", "A-1", "A-2", 3)
        assert error["lag_days"] == 3
        assert "lag of 3 days" in error["error"]

    def test_says_nothing_about_a_zero_lag(self):
        error = date_violation_error("blocked_by", "A-1", "A-2")
        assert error["lag_days"] == 0
        assert "lag" not in error["error"]
