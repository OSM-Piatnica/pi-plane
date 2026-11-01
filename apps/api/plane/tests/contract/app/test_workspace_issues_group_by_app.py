# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The work items of a workspace (My work items, workspace views) grouped like the lists of a project."""

import datetime
from unittest import mock

import pytest

from plane.db.models import Issue, Project, ProjectMember, State

ADMIN = 20


def _project(workspace, create_user, identifier):
    project = Project.objects.create(
        name=identifier, identifier=identifier, workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


@pytest.fixture
def projects(workspace, create_user):
    return _project(workspace, create_user, "AAA"), _project(workspace, create_user, "BBB")


def _issue(workspace, project, name, **dates):
    return Issue.objects.create(
        name=name, project=project, workspace=workspace, state=State.objects.get(project=project), **dates
    )


def _grouped(response):
    assert response.status_code == 200, response.data
    return {group: sorted(row["name"] for row in value["results"]) for group, value in response.data["results"].items()}


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkspaceIssuesGroupBy:
    def _get(self, session_client, workspace, **params):
        return session_client.get(
            f"/api/workspaces/{workspace.slug}/issues/", {"per_page": 50, "cursor": "50:0:0", **params}
        )

    def test_without_a_group_by_the_list_is_what_it_was(self, session_client, workspace, projects):
        _issue(workspace, projects[0], "one")

        response = self._get(session_client, workspace)

        assert response.status_code == 200, response.data
        assert [row["name"] for row in response.data["results"]] == ["one"]

    def test_work_items_of_several_projects_are_grouped_by_project(self, session_client, workspace, projects):
        _issue(workspace, projects[0], "in a")
        _issue(workspace, projects[1], "in b")

        grouped = _grouped(self._get(session_client, workspace, group_by="project_id"))

        assert grouped[str(projects[0].id)] == ["in a"]
        assert grouped[str(projects[1].id)] == ["in b"]

    def test_work_items_are_grouped_by_the_bucket_of_a_date(self, session_client, workspace, projects):
        today = datetime.date(2026, 3, 4)  # a Wednesday
        _issue(workspace, projects[0], "past", target_date=today - datetime.timedelta(days=2))
        _issue(workspace, projects[1], "soon", target_date=today + datetime.timedelta(days=1))
        _issue(workspace, projects[1], "undated")

        with mock.patch("plane.utils.date_buckets.timezone.localdate", return_value=today):
            grouped = _grouped(self._get(session_client, workspace, group_by="target_date_bucket"))

        assert grouped["earlier"] == ["past"]
        assert grouped["this_week"] == ["soon"]
        assert grouped["no_date"] == ["undated"]

    def test_the_week_of_the_workspace_decides_where_a_bucket_ends(self, session_client, workspace, projects):
        # 2026-03-08 is a Sunday: the last day of a week that starts on Monday, the first of one that starts on Sunday
        today = datetime.date(2026, 3, 8)
        _issue(workspace, projects[0], "midweek", target_date=datetime.date(2026, 3, 11))

        results = {}
        for start_of_the_week in (0, 1):
            type(workspace).objects.filter(pk=workspace.pk).update(start_of_the_week=start_of_the_week)
            with mock.patch("plane.utils.date_buckets.timezone.localdate", return_value=today):
                results[start_of_the_week] = _grouped(
                    self._get(session_client, workspace, group_by="target_date_bucket")
                )

        assert results[0]["this_week"] == ["midweek"]
        assert results[1]["next_week"] == ["midweek"]

    def test_a_load_more_request_of_one_bucket_stays_in_the_workspace(self, session_client, workspace, projects):
        _issue(workspace, projects[0], "undated one")
        _issue(workspace, projects[1], "dated", target_date=datetime.date(2030, 1, 1))

        response = self._get(session_client, workspace, target_date_bucket="no_date")

        assert response.status_code == 200, response.data
        assert [row["name"] for row in response.data["results"]] == ["undated one"]

    def test_the_same_group_and_sub_group_is_refused(self, session_client, workspace, projects):
        response = self._get(session_client, workspace, group_by="project_id", sub_group_by="project_id")

        assert response.status_code == 400
