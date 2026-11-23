# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The ``is_critical`` filter of the work item lists: the critical work items of the schedule analysis.

June 2027: 1 June is a Tuesday, the Mondays are 7, 14, 21 and 28 June.
"""

import json
from datetime import date
from unittest import mock

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueRelation,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

ADMIN, GUEST = 20, 5


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Critical", identifier="CRT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


def make_issue(project, author, name, start=None, finish=None):
    issue = Issue(
        name=name,
        project=project,
        workspace=project.workspace,
        state=State.objects.get(project=project),
        start_date=date.fromisoformat(start) if start else None,
        finish_date=date.fromisoformat(finish) if finish else None,
    )
    issue.save(created_by_id=author.id)
    return issue


@pytest.fixture
def issues(project, create_user):
    """A then B end on 9 and 11 June; D runs until 18 June and sets the end, so only D is critical.
    E has no dates."""
    a = make_issue(project, create_user, "A", "2027-06-07", "2027-06-09")
    b = make_issue(project, create_user, "B", "2027-06-10", "2027-06-11")
    d = make_issue(project, create_user, "D", "2027-06-07", "2027-06-18")
    e = make_issue(project, create_user, "E")
    IssueRelation.objects.create(
        issue=b,
        related_issue=a,
        relation_type="blocked_by",
        project=project,
        workspace=project.workspace,
    )
    return {"A": a, "B": b, "D": d, "E": e}


def names(response):
    assert response.status_code == 200, response.data
    return sorted(row["name"] for row in response.data["results"])


def project_list(client, project, **filters):
    url = f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/"
    return client.get(url, {"filters": json.dumps(filters)})


@pytest.mark.contract
@pytest.mark.django_db
class TestCriticalFilter:
    def test_true_finds_the_critical_work_items(self, session_client, project, issues):
        assert names(project_list(session_client, project, is_critical=True)) == ["D"]
        assert names(project_list(session_client, project, is_critical__exact=True)) == ["D"]

    def test_false_finds_every_other_work_item_also_those_without_dates(self, session_client, project, issues):
        assert names(project_list(session_client, project, is_critical=False)) == ["A", "B", "E"]

    def test_it_combines_with_other_filters(self, session_client, project, issues):
        both = {"and": [{"is_critical": True}, {"priority": "none"}]}
        response = session_client.get(
            f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/", {"filters": json.dumps(both)}
        )
        assert names(response) == ["D"]
        both = {"and": [{"is_critical": False}, {"priority__in": "urgent,high"}]}
        response = session_client.get(
            f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/", {"filters": json.dumps(both)}
        )
        assert names(response) == []

    def test_a_module_list_is_judged_by_the_analysis_of_the_module(
        self, session_client, workspace, project, issues, create_user
    ):
        """With A and B alone in a module, B (the later finish) is the end of the module, so it is critical there."""
        module = Module.objects.create(name="M", project=project, workspace=workspace, created_by=create_user)
        for key in ("A", "B"):
            ModuleIssue.objects.create(module=module, issue=issues[key], project=project, workspace=workspace)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/modules/{module.id}/issues/"
        response = session_client.get(url, {"filters": json.dumps({"is_critical": True})})
        assert names(response) == ["A", "B"]
        # the chain A then B is the whole module, so both are critical in it, and D is not part of it at all
        response = session_client.get(url, {"filters": json.dumps({"is_critical": False})})
        assert names(response) == []

    def test_an_analysis_cut_off_at_its_limit_leaves_the_filter_out_and_says_so(self, session_client, project, issues):
        """It would only describe part of the plan, so it must not drop work items quietly: the list is not filtered
        by it, and the X-Ignored-Filters header names the filter."""
        from plane.utils.schedule_analysis import analyse_queryset

        with mock.patch("plane.utils.schedule_scope.analyse_queryset") as analyse:
            analyse.side_effect = lambda queryset, project_id, weekend_days: analyse_queryset(
                queryset, project_id, weekend_days, max_items=2
            )
            for value in (True, False):
                response = project_list(session_client, project, is_critical=value)
                assert names(response) == ["A", "B", "D", "E"]
                assert response["X-Ignored-Filters"] == "is_critical"
            # the other conditions still apply
            both = {"and": [{"is_critical": True}, {"priority": "urgent"}]}
            response = session_client.get(
                f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/",
                {"filters": json.dumps(both)},
            )
            assert names(response) == []
            assert response["X-Ignored-Filters"] == "is_critical"

    def test_no_header_when_nothing_was_left_out(self, session_client, project, issues):
        assert "X-Ignored-Filters" not in project_list(session_client, project, is_critical=True)
        assert "X-Ignored-Filters" not in project_list(session_client, project)

    def test_it_needs_a_list_of_one_project(self, session_client, workspace, project, issues):
        """A global view mixes projects, so there is no single critical path to filter by."""
        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/issues/", {"filters": json.dumps({"is_critical": True})}
        )
        assert response.status_code == 400
        assert "critical_filter_needs_project" in json.dumps(response.data)

    def test_a_restricted_guest_gets_the_critical_path_of_their_own_work_items(self, workspace, project, issues):
        guest = User.objects.create(email="guest-critical@plane.so", username="guest_critical")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=GUEST)
        ProjectMember.objects.create(project=project, member=guest, workspace=workspace, role=GUEST, is_active=True)
        make_issue(project, guest, "Mine", "2027-06-07", "2027-06-08")
        client = APIClient()
        client.force_authenticate(user=guest)
        # the others' longer work items do not push the end of the guest's plan
        assert names(project_list(client, project, is_critical=True)) == ["Mine"]
