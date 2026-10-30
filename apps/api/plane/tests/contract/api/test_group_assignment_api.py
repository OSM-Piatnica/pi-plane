# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests: work items assigned to user groups through the public API (group_assignee_ids)."""

from uuid import uuid4

import pytest
from rest_framework import status

from plane.celery import app as celery_app
from plane.db.models import (
    Issue,
    IssueGroupAssignee,
    Project,
    ProjectGroup,
    ProjectMember,
    State,
    UserGroup,
    Workspace,
)

ADMIN, MEMBER = 20, 15
ASSIGNABLE_ERROR = {"error": "A work item can only be assigned to groups that are members of its project."}


@pytest.fixture(autouse=True)
def celery_eager():
    """Run Celery tasks in-process: there is no broker here and the tests only check the HTTP contract."""
    original_always_eager = celery_app.conf.task_always_eager
    original_eager_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    yield
    celery_app.conf.task_always_eager = original_always_eager
    celery_app.conf.task_eager_propagates = original_eager_propagates


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Groups", identifier="GAP", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Backlog",
        color="#000000",
        group="backlog",
        default=True,
        project=project,
        workspace=workspace,
        created_by=create_user,
    )
    return project


@pytest.fixture
def issue(db, project, workspace, create_user):
    return Issue.objects.create(name="Existing", project=project, workspace=workspace, created_by=create_user)


def _group(workspace, name, parent=None):
    return UserGroup.objects.create(workspace=workspace, name=name, parent=parent)


def _link(project, group, role=MEMBER):
    return ProjectGroup.objects.create(project=project, workspace=project.workspace, group=group, role=role)


def _list_url(workspace, project):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/issues/"


def _detail_url(workspace, project, issue):
    return f"{_list_url(workspace, project)}{issue.id}/"


def _assigned(issue):
    return set(IssueGroupAssignee.objects.filter(issue=issue).values_list("group_id", flat=True))


@pytest.mark.contract
@pytest.mark.django_db
class TestGroupAssigneesApi:
    def test_create_assigns_the_groups_and_the_answer_lists_them(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        _link(project, sales)

        response = api_key_client.post(
            _list_url(workspace, project),
            {"name": "Work", "group_assignee_ids": [str(sales.id), str(poland.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert set(response.data["group_assignee_ids"]) == {str(sales.id), str(poland.id)}
        assert _assigned(Issue.objects.get(pk=response.data["id"])) == {sales.id, poland.id}

    def test_a_work_item_without_groups_answers_an_empty_list(self, api_key_client, workspace, project):
        response = api_key_client.post(_list_url(workspace, project), {"name": "Plain"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["group_assignee_ids"] == []

    def test_a_group_that_is_not_in_the_project_is_refused_on_create(self, api_key_client, workspace, project):
        outside = _group(workspace, "Outside")

        response = api_key_client.post(
            _list_url(workspace, project), {"name": "Work", "group_assignee_ids": [str(outside.id)]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == ASSIGNABLE_ERROR
        assert not Issue.objects.filter(name="Work").exists()

    def test_patch_replaces_the_groups_and_an_empty_list_clears_them(self, api_key_client, workspace, project, issue):
        sales = _group(workspace, "Sales")
        support = _group(workspace, "Support")
        _link(project, sales)
        _link(project, support)
        url = _detail_url(workspace, project, issue)

        first = api_key_client.patch(url, {"group_assignee_ids": [str(sales.id)]}, format="json")
        assert first.status_code == status.HTTP_200_OK, first.data
        assert first.data["group_assignee_ids"] == [str(sales.id)]

        second = api_key_client.patch(url, {"group_assignee_ids": [str(support.id)]}, format="json")
        assert second.status_code == status.HTTP_200_OK
        assert _assigned(issue) == {support.id}

        cleared = api_key_client.patch(url, {"group_assignee_ids": []}, format="json")
        assert cleared.status_code == status.HTTP_200_OK
        assert _assigned(issue) == set()

    def test_patch_without_the_field_leaves_the_groups_alone(self, api_key_client, workspace, project, issue):
        sales = _group(workspace, "Sales")
        _link(project, sales)
        IssueGroupAssignee.objects.create(issue=issue, group=sales, project=project, workspace=workspace)

        response = api_key_client.patch(_detail_url(workspace, project, issue), {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert _assigned(issue) == {sales.id}

    def test_a_new_group_outside_the_project_is_refused_on_update_and_nothing_changes(
        self, api_key_client, workspace, project, issue
    ):
        sales = _group(workspace, "Sales")
        outside = _group(workspace, "Outside")
        _link(project, sales)
        IssueGroupAssignee.objects.create(issue=issue, group=sales, project=project, workspace=workspace)

        response = api_key_client.patch(
            _detail_url(workspace, project, issue),
            {"group_assignee_ids": [str(sales.id), str(outside.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == ASSIGNABLE_ERROR
        assert _assigned(issue) == {sales.id}

    def test_only_new_additions_are_validated_a_group_taken_out_of_the_project_stays(
        self, api_key_client, workspace, project, issue
    ):
        sales = _group(workspace, "Sales")
        link = _link(project, sales)
        support = _group(workspace, "Support")
        _link(project, support)
        IssueGroupAssignee.objects.create(issue=issue, group=sales, project=project, workspace=workspace)
        link.delete()

        response = api_key_client.patch(
            _detail_url(workspace, project, issue),
            {"group_assignee_ids": [str(sales.id), str(support.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert _assigned(issue) == {sales.id, support.id}

    def test_groups_of_another_workspace_and_unknown_ids_are_ignored(
        self, api_key_client, workspace, project, issue, create_user
    ):
        other = Workspace.objects.create(name="Other", slug="other", owner=create_user)
        foreign = _group(other, "Foreign")

        response = api_key_client.patch(
            _detail_url(workspace, project, issue),
            {"group_assignee_ids": [str(foreign.id), str(uuid4())]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert _assigned(issue) == set()

    def test_a_malformed_id_is_a_validation_error(self, api_key_client, workspace, project, issue):
        response = api_key_client.patch(
            _detail_url(workspace, project, issue), {"group_assignee_ids": ["not-a-uuid"]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_and_list_carry_the_groups(self, api_key_client, workspace, project, issue):
        sales = _group(workspace, "Sales")
        _link(project, sales)
        IssueGroupAssignee.objects.create(issue=issue, group=sales, project=project, workspace=workspace)

        detail = api_key_client.get(_detail_url(workspace, project, issue))
        listed = api_key_client.get(_list_url(workspace, project))

        assert detail.status_code == status.HTTP_200_OK
        assert detail.data["group_assignee_ids"] == [str(sales.id)]
        assert listed.status_code == status.HTTP_200_OK
        entry = next(e for e in listed.data["results"] if e["id"] == str(issue.id))
        assert entry["group_assignee_ids"] == [str(sales.id)]
