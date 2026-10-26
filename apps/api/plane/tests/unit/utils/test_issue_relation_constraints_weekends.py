# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Relation rules count working days: the weekend days of the dependent work item are skipped."""

from datetime import date, timedelta

import pytest

from plane.utils.issue_relation_constraints import (
    is_blocked_by_satisfied,
    is_finish_before_satisfied,
    is_start_before_finish_satisfied,
    is_start_before_satisfied,
    is_timeline_relation_satisfied,
)
from plane.utils.work_item_duration import effective_finish, effective_start, shift_working_days

SAT_SUN = [6, 0]
MONDAY = date(2026, 11, 2)  # a Monday


def day(offset):
    return MONDAY + timedelta(days=offset)


FRI, SAT, SUN, NEXT_MON, NEXT_TUE, NEXT_WED = day(4), day(5), day(6), day(7), day(8), day(9)


@pytest.mark.unit
class TestShiftHelpers:
    def test_a_positive_shift_counts_the_working_days_passed(self):
        assert shift_working_days(FRI, 1, SAT_SUN) == NEXT_MON
        assert shift_working_days(FRI, 3, SAT_SUN) == NEXT_WED
        assert shift_working_days(SAT, 1, SAT_SUN) == NEXT_MON

    def test_a_negative_shift_goes_back(self):
        assert shift_working_days(NEXT_MON, -1, SAT_SUN) == FRI
        assert shift_working_days(SUN, -1, SAT_SUN) == FRI

    def test_no_shift_is_the_day_itself(self):
        assert shift_working_days(SAT, 0, SAT_SUN) == SAT

    def test_without_weekend_days_it_is_plain_addition(self):
        assert shift_working_days(FRI, 3) == FRI + timedelta(days=3)
        assert shift_working_days(FRI, -3, []) == FRI - timedelta(days=3)

    def test_a_start_or_finish_on_a_weekend_day_stands_for_the_nearest_working_day(self):
        assert effective_start(SAT, SAT_SUN) == NEXT_MON
        assert effective_start(FRI, SAT_SUN) == FRI
        assert effective_finish(SUN, SAT_SUN) == FRI
        assert effective_finish(FRI, SAT_SUN) == FRI


@pytest.mark.unit
class TestBlockedBy:
    def test_the_blocked_item_may_start_on_the_working_day_after_the_blocker_finishes(self):
        assert is_blocked_by_satisfied(NEXT_MON, FRI, 0, SAT_SUN)

    def test_starting_on_the_day_the_blocker_finishes_is_still_too_early(self):
        assert not is_blocked_by_satisfied(FRI, FRI, 0, SAT_SUN)

    def test_a_start_on_the_weekend_counts_as_the_next_working_day(self):
        # a Saturday start was fine when every day counted, and stays fine: it is Monday for all intents
        assert is_blocked_by_satisfied(SAT, FRI, 0, SAT_SUN)
        assert is_blocked_by_satisfied(SUN, FRI, 0, SAT_SUN)

    def test_a_blocker_finishing_on_the_weekend_ended_on_the_last_working_day(self):
        assert is_blocked_by_satisfied(NEXT_MON, SAT, 0, SAT_SUN)
        assert is_blocked_by_satisfied(NEXT_MON, SUN, 0, SAT_SUN)

    def test_a_lag_counts_working_days(self):
        # two free working days between Friday and the start: Monday and Tuesday, so Wednesday is the earliest
        assert not is_blocked_by_satisfied(NEXT_TUE, FRI, 2, SAT_SUN)
        assert is_blocked_by_satisfied(NEXT_WED, FRI, 2, SAT_SUN)

    def test_a_lead_lets_them_share_a_working_day(self):
        assert is_blocked_by_satisfied(FRI, FRI, -1, SAT_SUN)
        assert not is_blocked_by_satisfied(day(3), FRI, -1, SAT_SUN)  # Thursday, before the blocker ends

    def test_without_weekend_days_every_day_counts_as_before(self):
        assert is_blocked_by_satisfied(SAT, FRI, 0)
        assert not is_blocked_by_satisfied(FRI, FRI, 0)
        assert is_blocked_by_satisfied(SAT, FRI, 0, [])


@pytest.mark.unit
class TestOtherRules:
    def test_start_to_start_lag_counts_working_days(self):
        # one working day after a Friday start is Monday
        assert is_start_before_satisfied(FRI, NEXT_MON, 1, SAT_SUN)
        assert not is_start_before_satisfied(FRI, FRI, 1, SAT_SUN)

    def test_finish_to_finish_lag_counts_working_days(self):
        assert is_finish_before_satisfied(FRI, NEXT_MON, 1, SAT_SUN)
        assert not is_finish_before_satisfied(FRI, NEXT_MON, 2, SAT_SUN)

    def test_start_to_finish_lag_counts_working_days(self):
        assert is_start_before_finish_satisfied(FRI, NEXT_MON, 1, SAT_SUN)
        assert not is_start_before_finish_satisfied(FRI, NEXT_MON, 2, SAT_SUN)

    def test_a_finish_on_the_weekend_ended_on_the_last_working_day(self):
        # the related item finishing on Sunday finished on Friday, so it is not a working day after the issue's Friday
        assert not is_finish_before_satisfied(FRI, SUN, 1, SAT_SUN)

    def test_missing_dates_never_block(self):
        assert is_blocked_by_satisfied(None, FRI, 0, SAT_SUN)
        assert is_start_before_satisfied(FRI, None, 0, SAT_SUN)


@pytest.mark.unit
class TestWhichCalendarApplies:
    """A rule limits the work item that comes later, so its project's weekend days are the ones that count."""

    def test_blocked_by_uses_the_issues_own_days(self):
        issue = {"start_date": SAT, "target_date": None}
        related = {"start_date": None, "target_date": FRI}

        # the issue (blocked) works Saturdays: its Saturday start is a real day, after the blocker's Friday finish
        assert is_timeline_relation_satisfied("blocked_by", issue, related, 0, [0], [0, 6])
        # with Saturday off for the issue the start is Monday: still fine; with no weekend and a Friday start it is not
        assert not is_timeline_relation_satisfied(
            "blocked_by", {"start_date": FRI, "target_date": None}, related, 0, [], [0, 6]
        )

    def test_blocking_uses_the_related_items_days(self):
        issue = {"start_date": None, "target_date": FRI}  # the blocker
        related = {"start_date": SAT, "target_date": None}  # the blocked item

        assert is_timeline_relation_satisfied("blocking", issue, related, 0, SAT_SUN, [0])  # works Saturdays
        assert is_timeline_relation_satisfied("blocking", issue, related, 0, [], SAT_SUN)  # Saturday is Monday

    def test_the_calendar_of_the_other_side_does_not_matter(self):
        issue = {"start_date": FRI, "target_date": None}
        related = {"start_date": None, "target_date": FRI}

        # blocked_by limits the issue: its own days (none off) make a Friday start too early, whatever the blocker's
        assert not is_timeline_relation_satisfied("blocked_by", issue, related, 0, [], SAT_SUN)
        assert not is_timeline_relation_satisfied("blocked_by", issue, related, 0, [], [])
