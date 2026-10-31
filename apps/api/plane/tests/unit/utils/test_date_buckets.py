# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import datetime

import pytest

from plane.utils.date_buckets import BUCKETS, bucket_bounds


MONDAY, SUNDAY, SATURDAY = 1, 0, 6


@pytest.mark.unit
class TestBucketBounds:
    # 2026-03-04 is a Wednesday
    TODAY = datetime.date(2026, 3, 4)

    def test_the_week_runs_monday_to_sunday(self):
        bounds = bucket_bounds(self.TODAY, MONDAY)

        assert bounds["today"] == (self.TODAY, self.TODAY)
        assert bounds["this_week"] == (datetime.date(2026, 3, 5), datetime.date(2026, 3, 8))
        assert bounds["next_week"] == (datetime.date(2026, 3, 9), datetime.date(2026, 3, 15))

    def test_earlier_and_later_are_open_on_one_side(self):
        bounds = bucket_bounds(self.TODAY, MONDAY)

        assert bounds["earlier"] == (None, datetime.date(2026, 3, 3))
        assert bounds["later"] == (datetime.date(2026, 3, 16), None)

    def test_on_a_sunday_this_week_is_empty_and_next_week_starts_tomorrow(self):
        sunday = datetime.date(2026, 3, 8)
        bounds = bucket_bounds(sunday, MONDAY)

        assert bounds["this_week"][0] > bounds["this_week"][1]
        assert bounds["next_week"] == (datetime.date(2026, 3, 9), datetime.date(2026, 3, 15))

    def test_every_bucket_is_known(self):
        assert set(BUCKETS) == {"earlier", "today", "this_week", "next_week", "later", "no_date"}


@pytest.mark.unit
class TestWeekStart:
    # 2026-03-04 is a Wednesday
    TODAY = datetime.date(2026, 3, 4)

    def test_a_week_that_starts_on_sunday_ends_on_saturday(self):
        bounds = bucket_bounds(self.TODAY, SUNDAY)

        assert bounds["this_week"] == (datetime.date(2026, 3, 5), datetime.date(2026, 3, 7))
        assert bounds["next_week"] == (datetime.date(2026, 3, 8), datetime.date(2026, 3, 14))

    def test_a_week_that_starts_on_saturday_ends_on_friday(self):
        bounds = bucket_bounds(self.TODAY, SATURDAY)

        assert bounds["this_week"] == (datetime.date(2026, 3, 5), datetime.date(2026, 3, 6))
        assert bounds["next_week"] == (datetime.date(2026, 3, 7), datetime.date(2026, 3, 13))

    def test_on_the_last_day_of_the_week_this_week_is_empty(self):
        saturday = datetime.date(2026, 3, 7)
        bounds = bucket_bounds(saturday, SUNDAY)

        assert bounds["this_week"][0] > bounds["this_week"][1]
        assert bounds["next_week"] == (datetime.date(2026, 3, 8), datetime.date(2026, 3, 14))
