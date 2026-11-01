# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Grouping work items by their due or finish date into time buckets."""

import datetime

import pytest
from django.utils import timezone

from plane.db.models import Issue, Project, ProjectMember, State

ADMIN = 20


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Buckets", identifier="BKT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


@pytest.fixture
def issues(workspace, project):
    state = State.objects.get(project=project)
    today = timezone.localdate()
    end_of_week = today + datetime.timedelta(days=6 - today.weekday())
    days = {
        "past": today - datetime.timedelta(days=3),
        "today": today,
        "next-week": end_of_week + datetime.timedelta(days=3),
        "far": end_of_week + datetime.timedelta(days=30),
        "undated": None,
    }
    for name, day in days.items():
        Issue.objects.create(
            name=name, project=project, workspace=workspace, state=state, target_date=day, finish_date=day
        )
    return days


def _grouped(response):
    assert response.status_code == 200, response.data
    return {group: sorted(row["name"] for row in value["results"]) for group, value in response.data["results"].items()}


@pytest.mark.contract
@pytest.mark.django_db
@pytest.mark.parametrize("field", ["target_date", "finish_date"])
class TestDateBuckets:
    def _get(self, session_client, workspace, project, **params):
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"
        return session_client.get(url, {"per_page": 50, "cursor": "50:0:0", **params})

    def test_work_items_are_grouped_into_buckets(self, session_client, workspace, project, issues, field):
        grouped = _grouped(self._get(session_client, workspace, project, group_by=f"{field}_bucket"))

        assert grouped["earlier"] == ["past"]
        assert grouped["today"] == ["today"]
        assert grouped["next_week"] == ["next-week"]
        assert grouped["later"] == ["far"]
        assert grouped["no_date"] == ["undated"]

    def test_one_bucket_is_loaded_by_its_name(self, session_client, workspace, project, issues, field):
        response = self._get(session_client, workspace, project, **{f"{field}_bucket": "later"})

        assert response.status_code == 200, response.data
        assert [row["name"] for row in response.data["results"]] == ["far"]

    def test_the_no_date_bucket_finds_the_work_items_without_the_date(
        self, session_client, workspace, project, issues, field
    ):
        response = self._get(session_client, workspace, project, **{f"{field}_bucket": "no_date"})

        assert [row["name"] for row in response.data["results"]] == ["undated"]
