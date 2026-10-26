# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Durations count working days: the project's weekend days are skipped."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from plane.utils.work_item_duration import (
    add_working_days,
    calculate_start_date_from_duration,
    calculate_target_date_from_duration,
    calculate_work_item_duration,
    count_working_days,
    reconcile_work_item_duration,
    subtract_working_days,
)

SAT_SUN = [6, 0]
FRI_SAT = [5, 6]
MONDAY = date(2026, 11, 2)  # a Monday


def work_item(start_date=None, target_date=None, duration=None):
    return SimpleNamespace(start_date=start_date, target_date=target_date, duration=duration)


def day(offset):
    """The date ``offset`` days after Monday 2 November 2026."""
    return MONDAY + timedelta(days=offset)


@pytest.mark.unit
class TestCounting:
    def test_a_range_inside_a_week_counts_every_day(self):
        assert count_working_days(day(0), day(2), SAT_SUN) == 3  # Mon - Wed

    def test_a_weekend_inside_the_range_is_not_counted(self):
        assert count_working_days(day(4), day(7), SAT_SUN) == 2  # Fri - Mon
        assert count_working_days(day(0), day(7), SAT_SUN) == 6  # Mon - next Mon

    def test_whole_weeks_count_five_days(self):
        assert count_working_days(day(0), day(13), SAT_SUN) == 10

    def test_other_weekend_days_are_skipped_too(self):
        assert count_working_days(day(0), day(6), FRI_SAT) == 5  # Mon - Sun, Fri and Sat off
        assert count_working_days(day(0), day(6), [3]) == 6  # only Wednesday off

    def test_without_weekend_days_every_day_counts(self):
        assert count_working_days(day(0), day(6), []) == 7
        assert count_working_days(day(0), day(6)) == 7

    def test_a_backwards_range_has_none(self):
        assert count_working_days(day(3), day(0), SAT_SUN) == 0


@pytest.mark.unit
class TestMovingByWorkingDays:
    def test_forward_skips_the_weekend(self):
        assert add_working_days(day(0), 3, SAT_SUN) == day(2)  # Mon + 3 -> Wed
        assert add_working_days(day(4), 2, SAT_SUN) == day(7)  # Fri + 2 -> Mon
        assert add_working_days(day(0), 5, SAT_SUN) == day(4)  # a full week ends Friday

    def test_a_start_on_a_weekend_day_counts_from_the_next_working_day(self):
        assert add_working_days(day(5), 1, SAT_SUN) == day(7)  # Sat, one day -> Mon
        assert add_working_days(day(6), 2, SAT_SUN) == day(8)  # Sun, two days -> Tue

    def test_long_durations_jump_whole_weeks(self):
        assert add_working_days(day(0), 11, SAT_SUN) == day(14)  # eleventh working day is the Monday two weeks on
        assert add_working_days(day(0), 5000, SAT_SUN) == day(0) + timedelta(days=(4999 // 5) * 7 + 4999 % 5)

    def test_backward_skips_the_weekend(self):
        assert subtract_working_days(day(2), 3, SAT_SUN) == day(0)  # Wed - 3 -> Mon
        assert subtract_working_days(day(7), 2, SAT_SUN) == day(4)  # Mon - 2 -> Fri
        assert subtract_working_days(day(6), 1, SAT_SUN) == day(4)  # Sun, one day -> Fri

    def test_other_weekend_days(self):
        assert add_working_days(day(3), 2, FRI_SAT) == day(6)  # Thu, then Sunday: Friday and Saturday are off
        assert subtract_working_days(day(6), 2, FRI_SAT) == day(3)

    def test_a_week_with_every_day_off_does_not_trap(self):
        assert add_working_days(day(0), 3, [0, 1, 2, 3, 4, 5, 6]) == day(2)

    def test_going_out_and_back_agrees_for_every_start_and_length(self):
        for weekend in (SAT_SUN, FRI_SAT, [3], []):
            for start_offset in range(14):
                for length in range(1, 30):
                    start = day(start_offset)
                    target = add_working_days(start, length, weekend)
                    assert count_working_days(start, target, weekend) == length
                    assert count_working_days(subtract_working_days(target, length, weekend), target, weekend) == length


@pytest.mark.unit
class TestDuration:
    def test_counts_working_days(self):
        assert calculate_work_item_duration(day(0), day(7), SAT_SUN) == 6

    def test_a_range_made_only_of_weekend_days_lasts_one_day(self):
        assert calculate_work_item_duration(day(5), day(6), SAT_SUN) == 1

    def test_a_backwards_range_is_still_reported_as_such(self):
        assert calculate_work_item_duration(day(3), day(0), SAT_SUN) <= 0

    def test_without_weekend_days_nothing_changes(self):
        assert calculate_work_item_duration(day(0), day(7)) == 8

    def test_target_and_start_from_a_duration(self):
        assert calculate_target_date_from_duration(day(4), 2, SAT_SUN) == day(7).isoformat()
        assert calculate_start_date_from_duration(day(7), 2, SAT_SUN) == day(4).isoformat()


@pytest.mark.unit
class TestReconcile:
    def test_a_duration_edit_moves_the_target_over_the_weekend(self):
        derived = reconcile_work_item_duration(work_item(day(4), day(4), 1), {"duration": 3}, SAT_SUN)

        assert derived == {"duration": 3, "target_date": day(8).isoformat()}  # Fri, Mon, Tue

    def test_a_duration_edit_with_only_a_target_moves_the_start_back_over_the_weekend(self):
        derived = reconcile_work_item_duration(work_item(None, day(7), None), {"duration": 3}, SAT_SUN)

        assert derived == {"duration": 3, "start_date": day(3).isoformat()}  # Thu, Fri, Mon

    def test_a_date_edit_counts_working_days(self):
        derived = reconcile_work_item_duration(
            work_item(day(0), day(2), 3), {"target_date": day(9).isoformat()}, SAT_SUN
        )

        assert derived == {"duration": 8}  # Mon 2 - Wed 11 Nov, 8 working days

    def test_dates_across_a_weekend_only_give_one_day_when_nothing_else_is_working(self):
        derived = reconcile_work_item_duration(
            work_item(None, None, None), {"start_date": day(5).isoformat(), "target_date": day(6).isoformat()}, SAT_SUN
        )

        assert derived == {"duration": 1}

    def test_a_start_after_the_target_keeps_the_length_and_moves_the_target_by_working_days(self):
        derived = reconcile_work_item_duration(
            work_item(day(0), day(2), 3), {"start_date": day(4).isoformat()}, SAT_SUN
        )

        assert derived == {"duration": 3, "target_date": day(8).isoformat()}  # Fri + 3 working days

    def test_the_project_with_no_weekend_keeps_the_old_behaviour(self):
        derived = reconcile_work_item_duration(work_item(day(4), day(4), 1), {"duration": 3}, [])

        assert derived == {"duration": 3, "target_date": day(6).isoformat()}
