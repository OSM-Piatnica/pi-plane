# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Focus helpers that need no database: the list size, the overdue reasons, today and the holding rules."""

import datetime
from types import SimpleNamespace

import pytest

from plane.utils.focus import DEFAULT_LIMIT, HOLDING_RULES, MAX_LIMIT, clamp_limit, overdue_reasons, today_for
from plane.utils.issue_relation_constraints import STORED_TIMELINE_RELATION_TYPES
from plane.utils.issue_relation_types import INVERSE_RELATIONS

TODAY = datetime.date(2027, 6, 9)


@pytest.mark.unit
class TestFocusHelpers:
    @pytest.mark.parametrize(
        "raw, expected",
        [(None, DEFAULT_LIMIT), ("", DEFAULT_LIMIT), ("ten", DEFAULT_LIMIT), ("0", 1), ("-3", 1), ("20", 20)],
    )
    def test_the_limit_is_read_and_kept_in_bounds(self, raw, expected):
        assert clamp_limit(raw) == expected

    def test_the_limit_has_a_ceiling(self):
        assert clamp_limit(str(MAX_LIMIT + 1)) == MAX_LIMIT

    @pytest.mark.parametrize(
        "target, finish, expected",
        [
            (datetime.date(2027, 6, 8), datetime.date(2027, 6, 8), ["due", "finish"]),
            (datetime.date(2027, 6, 8), None, ["due"]),
            (None, datetime.date(2027, 6, 8), ["finish"]),
            (TODAY, TODAY, []),
            (None, None, []),
        ],
    )
    def test_overdue_reasons(self, target, finish, expected):
        assert overdue_reasons({"target_date": target, "finish_date": finish}, TODAY) == expected

    def test_today_falls_back_to_utc_for_an_unknown_time_zone(self):
        utc_today = datetime.datetime.now(datetime.UTC).date()
        assert today_for(SimpleNamespace(user_timezone="Nowhere/Never")) in {
            utc_today,
            utc_today - datetime.timedelta(days=1),
            utc_today + datetime.timedelta(days=1),
        }

    def test_every_timeline_relation_holds_something_up_and_is_named_from_the_held_up_side(self):
        assert set(HOLDING_RULES) == set(STORED_TIMELINE_RELATION_TYPES)
        for relation_type, rule in HOLDING_RULES.items():
            # the held-up work item is the successor; it sees the stored name, or its reverse when stored the other way
            expected = relation_type if not rule["predecessor_is_issue"] else INVERSE_RELATIONS[relation_type]
            assert rule["seen_as"] == expected, relation_type
