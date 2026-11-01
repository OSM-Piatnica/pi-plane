# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Time buckets for grouping work items by a date (start, due or finish date): earlier, today, this week, next week,
later and no date. "Today" is the calendar day in the active (user) time zone. A week begins on the start of the week
of the project being listed (else the workspace's), numbered like ``start_of_the_week``: 0 is Sunday, 1 is Monday
(the default).
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
NO_DATE = "no_date"

BUCKETS = (EARLIER, TODAY, THIS_WEEK, NEXT_WEEK, LATER, NO_DATE)

# Group by names (annotations) -> the date field they bucket
DEFAULT_WEEK_START = 1  # Monday, the default of a workspace and a project

BUCKET_FIELDS = {
    "start_date_bucket": "start_date",
    "target_date_bucket": "target_date",
    "finish_date_bucket": "finish_date",
}


def week_start_for_request(request):
    """
    The first day of the week the buckets of a list are counted by: the project of the list (taken from the URL),
    else the workspace of the URL, else Sunday. A list of several projects (a profile page) has no project and
    uses the workspace's, so the whole list shares one definition of "this week".
    """
    from plane.db.models import Project, Workspace

    context = getattr(request, "parser_context", None) or {}
    kwargs = context.get("kwargs") or {}
    value = None
    if kwargs.get("project_id"):
        value = Project.objects.filter(pk=kwargs["project_id"]).values_list("start_of_the_week", flat=True).first()
    if value is None and kwargs.get("slug"):
        value = Workspace.objects.filter(slug=kwargs["slug"]).values_list("start_of_the_week", flat=True).first()
    return DEFAULT_WEEK_START if value is None else value


def bucket_bounds(today=None, week_start=DEFAULT_WEEK_START):
    """The first and last day of each bucket that has both ends; earlier and later are open on one side."""
    today = today or timezone.localdate()
    # Python counts Monday as 0; the start of the week counts Sunday as 0
    days_into_week = ((today.weekday() + 1) % 7 - week_start) % 7
    end_of_week = today + datetime.timedelta(days=6 - days_into_week)
    end_of_next_week = end_of_week + datetime.timedelta(days=7)
    return {
        TODAY: (today, today),
        THIS_WEEK: (today + datetime.timedelta(days=1), end_of_week),
        NEXT_WEEK: (end_of_week + datetime.timedelta(days=1), end_of_next_week),
        # open ends
        EARLIER: (None, today - datetime.timedelta(days=1)),
        LATER: (end_of_next_week + datetime.timedelta(days=1), None),
    }


def bucket_q(field, bucket, today=None, week_start=DEFAULT_WEEK_START):
    """A Q on a date field for one bucket; an unknown bucket matches nothing."""
    if bucket == NO_DATE:
        return Q(**{f"{field}__isnull": True})
    bounds = bucket_bounds(today, week_start).get(bucket)
    if bounds is None:
        return Q(pk__in=[])
    first, last = bounds
    condition = Q(**{f"{field}__isnull": False})
    if first is not None:
        condition &= Q(**{f"{field}__gte": first})
    if last is not None:
        condition &= Q(**{f"{field}__lte": last})
    return condition


def bucket_case(field, today=None, week_start=DEFAULT_WEEK_START):
    """An expression that is the bucket of a date field."""
    return Case(
        *[
            When(bucket_q(field, bucket, today, week_start), then=Value(bucket))
            for bucket in BUCKETS
            if bucket != NO_DATE
        ],
        default=Value(NO_DATE),
        output_field=CharField(),
    )
