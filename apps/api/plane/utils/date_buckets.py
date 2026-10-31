# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Time buckets for grouping work items by a date (due or finish date): earlier, today, this week, next week, later
and no date. Weeks run Monday to Sunday and "today" is the calendar day in the active (user) time zone.
The web app has the same rules in ``packages/utils/src/date-bucket.ts``; keep the two in step.
"""

import datetime

from django.db.models import Case, CharField, Q, Value, When
from django.utils import timezone

EARLIER = "earlier"
TODAY = "today"
THIS_WEEK = "this_week"
NEXT_WEEK = "next_week"
LATER = "later"
NONE = "none"

BUCKETS = (EARLIER, TODAY, THIS_WEEK, NEXT_WEEK, LATER, NONE)

# Group by names (annotations) -> the date field they bucket
BUCKET_FIELDS = {
    "target_date_bucket": "target_date",
    "finish_date_bucket": "finish_date",
}


def bucket_bounds(today=None):
    """The first and last day of each bucket that has both ends; earlier and later are open on one side."""
    today = today or timezone.localdate()
    end_of_week = today + datetime.timedelta(days=6 - today.weekday())
    end_of_next_week = end_of_week + datetime.timedelta(days=7)
    return {
        TODAY: (today, today),
        THIS_WEEK: (today + datetime.timedelta(days=1), end_of_week),
        NEXT_WEEK: (end_of_week + datetime.timedelta(days=1), end_of_next_week),
        # open ends
        EARLIER: (None, today - datetime.timedelta(days=1)),
        LATER: (end_of_next_week + datetime.timedelta(days=1), None),
    }


def bucket_q(field, bucket, today=None):
    """A Q on a date field for one bucket; an unknown bucket matches nothing."""
    if bucket == NONE:
        return Q(**{f"{field}__isnull": True})
    bounds = bucket_bounds(today).get(bucket)
    if bounds is None:
        return Q(pk__in=[])
    first, last = bounds
    condition = Q(**{f"{field}__isnull": False})
    if first is not None:
        condition &= Q(**{f"{field}__gte": first})
    if last is not None:
        condition &= Q(**{f"{field}__lte": last})
    return condition


def bucket_case(field, today=None):
    """An expression that is the bucket of a date field."""
    return Case(
        *[When(bucket_q(field, bucket, today), then=Value(bucket)) for bucket in BUCKETS if bucket != NONE],
        default=Value(NONE),
        output_field=CharField(),
    )
