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
            name=name,
            project=project,
            workspace=workspace,
            state=state,
            start_date=day,
            target_date=day,
            finish_date=day,
        )
    return days


def _grouped(response):
    assert response.status_code == 200, response.data
    return {group: sorted(row["name"] for row in value["results"]) for group, value in response.data["results"].items()}


@pytest.mark.contract
@pytest.mark.django_db
@pytest.mark.parametrize("field", ["start_date", "target_date", "finish_date"])
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


@pytest.mark.contract
@pytest.mark.django_db
class TestDateBucketSubGroups:
    def test_work_items_are_sub_grouped_by_the_bucket_of_another_date(
        self, session_client, workspace, project, issues, create_user
    ):
        # the dates of "past" differ: its due date moves to next week, its finish date stays in the past
        past = Issue.objects.get(project=project, name="past")
        past.target_date = issues["next-week"]
        past.save()

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/",
            {
                "group_by": "target_date_bucket",
                "sub_group_by": "finish_date_bucket",
                "per_page": 50,
                "cursor": "50:0:0",
            },
        )

        assert response.status_code == 200, response.data
        groups = response.data["results"]
        assert [row["name"] for row in groups["next_week"]["results"]["earlier"]["results"]] == ["past"]
        assert [row["name"] for row in groups["next_week"]["results"]["next_week"]["results"]] == ["next-week"]
        assert [row["name"] for row in groups["today"]["results"]["today"]["results"]] == ["today"]

    def test_the_same_date_cannot_be_both_group_and_sub_group(self, session_client, workspace, project, issues):
        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/",
            {"group_by": "target_date_bucket", "sub_group_by": "target_date_bucket"},
        )

        assert response.status_code == 400
