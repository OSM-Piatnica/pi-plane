# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""How the per-bucket and schedule window filters of a work item list are put together."""

import datetime
import uuid
from types import SimpleNamespace

import pytest

from plane.utils.date_buckets import bucket_bounds, bucket_lookups
from plane.utils.issue_filters import issue_filters

PROJECT_ID = uuid.uuid4()


def _request(**kwargs):
    return SimpleNamespace(parser_context={"kwargs": kwargs})


@pytest.mark.unit
class TestBucketLookups:
    TODAY = datetime.date(2026, 3, 4)

    def test_a_bucket_is_plain_date_lookups(self):
        bounds = bucket_bounds(self.TODAY, 1)

        assert bucket_lookups("target_date", "this_week", self.TODAY, 1) == {
            "target_date__gte": bounds["this_week"][0],
            "target_date__lte": bounds["this_week"][1],
        }

    def test_earlier_and_later_are_open_on_one_side(self):
        assert list(bucket_lookups("finish_date", "earlier", self.TODAY, 1)) == ["finish_date__lte"]
        assert list(bucket_lookups("finish_date", "later", self.TODAY, 1)) == ["finish_date__gte"]

    def test_no_date_is_a_null_check_and_an_unknown_bucket_is_nothing(self):
        assert bucket_lookups("start_date", "no_date") == {"start_date__isnull": True}
        assert bucket_lookups("start_date", "someday") is None


@pytest.mark.unit
@pytest.mark.django_db
class TestIssueFilters:
    def test_a_bucket_filters_the_list_directly_without_a_subquery(self):
        filters = issue_filters({"target_date_bucket": "no_date"}, "GET", request=_request(project_id=PROJECT_ID))

        assert filters == {"target_date__isnull": True}

    def test_a_bucket_and_another_filter_on_the_same_date_both_hold(self):
        filters = issue_filters(
            {"target_date_bucket": "later", "target_date": "2026-01-01;after"},
            "GET",
            request=_request(project_id=PROJECT_ID),
        )

        # the plain lookup of the date filter stays, the bucket goes into a subquery
        assert "target_date__gte" in filters
        assert "pk__in" in filters

    def test_the_subquery_of_the_schedule_window_is_limited_to_the_project_of_the_list(self):
        filters = issue_filters(
            {"schedule_window": "2026-03-01;2026-03-31"}, "GET", request=_request(project_id=PROJECT_ID)
        )

        sql = str(filters["pk__in"].query)
        assert "project_id" in sql
        assert str(PROJECT_ID) in sql

    def test_without_a_project_the_subquery_is_limited_to_the_workspace(self):
        filters = issue_filters({"schedule_window": "2026-03-01;2026-03-31"}, "GET", request=_request(slug="acme"))

        assert "acme" in str(filters["pk__in"].query)

    def test_an_unknown_bucket_matches_nothing(self):
        filters = issue_filters({"finish_date_bucket": "someday"}, "GET", request=_request(project_id=PROJECT_ID))

        assert "pk__in" in filters
