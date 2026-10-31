# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Work items assigned to user groups: the assignment itself, and what belonging to such a group lets someone do."""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueGroupAssignee,
    Project,
    ProjectGroup,
    ProjectMember,
    State,
    User,
    UserGroup,
    UserGroupMember,
    Workspace,
    WorkspaceMember,
)

ADMIN, MEMBER = 20, 15


@pytest.fixture(autouse=True)
def _no_background_work(db):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch("plane.app.views.issue.worklog.issue_activity"),
        mock.patch("plane.db.mixins.soft_delete_related_objects.delay"),
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Groups",
        identifier="GRP",
        workspace=workspace,
        created_by=create_user,
        is_assignee_edit_rule_enabled=True,
        is_time_tracking_enabled=True,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


@pytest.fixture
def issue(project, workspace):
    return Issue.objects.create(
        name="Shared", project=project, workspace=workspace, state=State.objects.get(project=project)
    )


def _member(workspace, project, email):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=MEMBER)
    ProjectMember.objects.create(project=project, member=user, role=MEMBER, workspace=workspace, is_active=True)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _group(workspace, name, parent=None):
    """A group; its projects have it as a member, since work items can only go to groups of their project."""
    group = UserGroup.objects.create(workspace=workspace, name=name, parent=parent)
    for project in Project.objects.filter(workspace=workspace):
        ProjectGroup.objects.create(project=project, group=group, role=MEMBER)
    return group


def _join(group, user):
    UserGroupMember.objects.create(workspace=group.workspace, group=group, user=user)


def _issue_url(workspace, project, issue, suffix=""):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/{suffix}"


@pytest.mark.contract
@pytest.mark.django_db
class TestAssigningGroups:
    def test_a_work_item_is_assigned_to_groups_and_the_answer_lists_them(
        self, session_client, workspace, project, issue
    ):
        sales = _group(workspace, "Sales")
        support = _group(workspace, "Support")

        response = session_client.patch(
            _issue_url(workspace, project, issue),
            {"group_assignee_ids": [str(sales.id), str(support.id)]},
            format="json",
        )

        assert response.status_code == 204, getattr(response, "data", None)
        detail = session_client.get(_issue_url(workspace, project, issue))
        assert sorted(str(group_id) for group_id in detail.data["group_assignee_ids"]) == sorted(
            [str(sales.id), str(support.id)]
        )

    def test_a_new_list_replaces_the_old_one_and_an_empty_one_clears_it(
        self, session_client, workspace, project, issue
    ):
        sales = _group(workspace, "Sales")
        support = _group(workspace, "Support")
        url = _issue_url(workspace, project, issue)
        session_client.patch(url, {"group_assignee_ids": [str(sales.id)]}, format="json")

        session_client.patch(url, {"group_assignee_ids": [str(support.id)]}, format="json")
        assert [str(g) for g in session_client.get(url).data["group_assignee_ids"]] == [str(support.id)]

        session_client.patch(url, {"group_assignee_ids": []}, format="json")
        assert session_client.get(url).data["group_assignee_ids"] == []

    def test_a_group_of_another_workspace_is_ignored(self, session_client, workspace, project, issue, create_user):
        other = Workspace.objects.create(name="Other", slug="other", owner=create_user)
        foreign = _group(other, "Foreign")
        mine = _group(workspace, "Mine")

        session_client.patch(
            _issue_url(workspace, project, issue),
            {"group_assignee_ids": [str(foreign.id), str(mine.id)]},
            format="json",
        )

        assert list(IssueGroupAssignee.objects.filter(issue=issue).values_list("group_id", flat=True)) == [mine.id]

    def test_other_assignees_are_untouched_when_only_groups_change(self, session_client, workspace, project, issue):
        person = _member(workspace, project, "ada@example.com")
        IssueAssignee.objects.create(issue=issue, assignee=person, project=project, workspace=workspace)

        session_client.patch(
            _issue_url(workspace, project, issue),
            {"group_assignee_ids": [str(_group(workspace, "Sales").id)]},
            format="json",
        )

        assert IssueAssignee.objects.filter(issue=issue, assignee=person).exists()

    def test_the_list_carries_the_groups_and_can_be_filtered_by_them(self, session_client, workspace, project, issue):
        sales = _group(workspace, "Sales")
        other_issue = Issue.objects.create(
            name="Other", project=project, workspace=workspace, state=State.objects.get(project=project)
        )
        IssueGroupAssignee.objects.create(issue=issue, group=sales, project=project, workspace=workspace)
        base = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"

        everything = session_client.get(base)
        filtered = session_client.get(base, {"group_assignees": str(sales.id)})

        rows = {row["name"]: row for row in everything.data["results"]}
        assert [str(g) for g in rows["Shared"]["group_assignee_ids"]] == [str(sales.id)]
        assert rows["Other"]["group_assignee_ids"] == []
        assert [row["name"] for row in filtered.data["results"]] == ["Shared"]
        assert other_issue.name == "Other"


@pytest.mark.contract
@pytest.mark.django_db
class TestBelongingToAnAssignedGroup:
    def _assigned_to(self, workspace, project, issue, group):
        IssueGroupAssignee.objects.create(issue=issue, group=group, project=project, workspace=workspace)

    def test_a_member_of_the_assigned_group_may_change_the_work_item_under_the_edit_rule(
        self, workspace, project, issue
    ):
        sales = _group(workspace, "Sales")
        insider = _member(workspace, project, "in@example.com")
        outsider = _member(workspace, project, "out@example.com")
        _join(sales, insider)
        self._assigned_to(workspace, project, issue, sales)
        url = _issue_url(workspace, project, issue)

        assert _client(insider).patch(url, {"name": "Renamed"}, format="json").status_code == 204
        assert _client(outsider).patch(url, {"name": "Hijacked"}, format="json").status_code == 403

    def test_a_member_of_a_subgroup_belongs_to_the_group_above_it(self, workspace, project, issue):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        person = _member(workspace, project, "pl@example.com")
        _join(poland, person)
        self._assigned_to(workspace, project, issue, sales)

        response = _client(person).patch(_issue_url(workspace, project, issue), {"name": "Renamed"}, format="json")

        assert response.status_code == 204

    def test_a_group_assignment_keeps_the_item_from_being_open_to_everyone(self, workspace, project, issue):
        outsider = _member(workspace, project, "out@example.com")
        self._assigned_to(workspace, project, issue, _group(workspace, "Sales"))

        response = _client(outsider).patch(_issue_url(workspace, project, issue), {"name": "x"}, format="json")

        assert response.status_code == 403

    def test_only_the_members_of_the_assigned_group_can_log_time(self, workspace, project, issue):
        sales = _group(workspace, "Sales")
        insider = _member(workspace, project, "in@example.com")
        outsider = _member(workspace, project, "out@example.com")
        _join(sales, insider)
        self._assigned_to(workspace, project, issue, sales)
        url = _issue_url(workspace, project, issue, "worklogs/")

        assert _client(insider).post(url, {"duration": 10}, format="json").status_code == 201
        assert _client(outsider).post(url, {"duration": 10}, format="json").status_code == 403
