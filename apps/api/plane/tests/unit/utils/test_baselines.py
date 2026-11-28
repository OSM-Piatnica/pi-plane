# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Variance against a baseline, in working days.

June 2027: 1 June is a Tuesday; 4 June is a Friday, 5 and 6 June the weekend, 7 June a Monday.
"""

from datetime import date

import pytest

from plane.utils.baselines import compute_variance, working_day_difference
from plane.utils.work_item_duration import effective_start

WEEKEND = [0, 6]


def day(number):
    return date(2027, 6, number)


def dates(start=None, finish=None, due=None):
    return {
        "start_date": day(start) if start else None,
        "finish_date": day(finish) if finish else None,
        "target_date": day(due) if due else None,
    }


@pytest.mark.unit
class TestWorkingDayDifference:
    def test_the_same_day_is_no_change(self):
        assert working_day_difference(day(2), day(2), WEEKEND) == 0

    def test_later_is_positive_and_earlier_negative(self):
        assert working_day_difference(day(1), day(3), WEEKEND) == 2
        assert working_day_difference(day(3), day(1), WEEKEND) == -2

    def test_a_weekend_on_the_way_is_not_counted(self):
        # Friday to Monday is one working day, and to the Monday a week later six
        assert working_day_difference(day(4), day(7), WEEKEND) == 1
        assert working_day_difference(day(4), day(14), WEEKEND) == 6
        assert working_day_difference(day(7), day(4), WEEKEND) == -1
        assert working_day_difference(day(14), day(2), WEEKEND) == -8

    def test_without_weekend_days_every_day_counts(self):
        assert working_day_difference(day(4), day(7), []) == 3
        assert working_day_difference(day(4), day(7)) == 3

    def test_the_weekend_days_of_the_project_are_used(self):
        # Friday and Saturday off: Thursday 3 June to Sunday 6 June is one working day
        assert working_day_difference(day(3), day(6), [5, 6]) == 1

    def test_a_finish_on_a_weekend_day_counts_as_the_working_day_before(self):
        # Friday to Saturday or Sunday is no change; Saturday to Monday is the one day from Friday to Monday
        assert working_day_difference(day(4), day(5), WEEKEND) == 0
        assert working_day_difference(day(4), day(6), WEEKEND) == 0
        assert working_day_difference(day(5), day(7), WEEKEND) == 1
        assert working_day_difference(day(6), day(4), WEEKEND) == 0

    def test_a_start_on_a_weekend_day_counts_as_the_working_day_after(self):
        assert working_day_difference(day(5), day(7), WEEKEND, effective_start) == 0
        assert working_day_difference(day(4), day(5), WEEKEND, effective_start) == 1
        assert working_day_difference(day(7), day(5), WEEKEND, effective_start) == 0

    def test_a_missing_date_has_no_difference(self):
        assert working_day_difference(None, day(2), WEEKEND) is None
        assert working_day_difference(day(2), None, WEEKEND) is None


@pytest.mark.unit
class TestComputeVariance:
    def test_dates_and_variances_of_a_moved_work_item(self):
        items, summary = compute_variance(
            {"A": dates(1, 4, 11)},
            [{"id": "A", **dates(3, 9, 11)}],
            WEEKEND,
        )
        assert items == {
            "A": {
                "in_baseline": True,
                "baseline_start_date": "2027-06-01",
                "start_date": "2027-06-03",
                "start_date_variance": 2,
                "baseline_finish_date": "2027-06-04",
                "finish_date": "2027-06-09",
                # Friday 4 June to Wednesday 9 June: Monday, Tuesday, Wednesday
                "finish_date_variance": 3,
                "baseline_target_date": "2027-06-11",
                "target_date": "2027-06-11",
            }
        }
        assert summary == {"baseline_end": "2027-06-04", "current_end": "2027-06-09", "end_variance": 3}

    def test_a_moved_due_date_is_answered_but_is_no_variance(self):
        items, summary = compute_variance({"A": dates(1, 4, 11)}, [{"id": "A", **dates(1, 4, 18)}], WEEKEND)
        assert (items["A"]["baseline_target_date"], items["A"]["target_date"]) == ("2027-06-11", "2027-06-18")
        assert "target_date_variance" not in items["A"]
        assert (items["A"]["start_date_variance"], items["A"]["finish_date_variance"]) == (0, 0)
        assert summary["end_variance"] == 0

    def test_a_date_set_or_cleared_since_has_no_variance(self):
        items, _ = compute_variance({"A": dates(1, None)}, [{"id": "A", **dates(None, 4)}], WEEKEND)
        assert items["A"]["start_date_variance"] is None
        assert items["A"]["finish_date_variance"] is None
        assert (items["A"]["baseline_start_date"], items["A"]["start_date"]) == ("2027-06-01", None)
        assert (items["A"]["baseline_finish_date"], items["A"]["finish_date"]) == (None, "2027-06-04")

    def test_a_work_item_the_baseline_does_not_know(self):
        items, summary = compute_variance({}, [{"id": "New", **dates(1, 2)}, {"id": "Undated", **dates()}], WEEKEND)
        assert set(items) == {"New"}
        assert items["New"]["in_baseline"] is False
        assert items["New"]["baseline_start_date"] is None
        assert items["New"]["start_date_variance"] is None
        assert summary == {"baseline_end": None, "current_end": "2027-06-02", "end_variance": None}

    def test_a_work_item_that_lost_its_dates_is_still_compared(self):
        items, _ = compute_variance({"A": dates(1, 2)}, [{"id": "A", **dates()}], WEEKEND)
        assert items["A"]["in_baseline"] is True
        assert items["A"]["baseline_finish_date"] == "2027-06-02"
        assert items["A"]["finish_date"] is None

    def test_work_items_gone_since_are_left_out_also_of_the_end(self):
        items, summary = compute_variance(
            {"A": dates(1, 2), "Gone": dates(1, 30)},
            [{"id": "A", **dates(1, 3)}],
            WEEKEND,
        )
        assert set(items) == {"A"}
        assert summary == {"baseline_end": "2027-06-02", "current_end": "2027-06-03", "end_variance": 1}

    def test_the_end_is_the_latest_finish_then_and_now(self):
        _, summary = compute_variance(
            {"A": dates(1, 4), "B": dates(1, 10)},
            [{"id": "A", **dates(1, 8)}, {"id": "B", **dates(1, 3)}, {"id": "C", **dates(1, 7)}],
            WEEKEND,
        )
        # the plan ended on Thursday 10 June and ends on Tuesday 8 June now
        assert summary == {"baseline_end": "2027-06-10", "current_end": "2027-06-08", "end_variance": -2}
