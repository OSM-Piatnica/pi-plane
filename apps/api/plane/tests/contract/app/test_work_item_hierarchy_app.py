# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the Epic tests of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""Contract tests for the parent rules of a work item.

A work item cannot be its own parent, a parent change cannot close a cycle, parent and child
belong to one project, an Epic has no parent, and the sub-work-item endpoint attaches all or none.
"""

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueType, Project, ProjectIssueType, ProjectMember
from plane.utils.work_item_hierarchy import MAX_SUB_WORK_ITEMS_PER_REQUEST

SUB_ISSUES_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/sub-issues/"
ISSUE_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"


def _make_issue(name, project, workspace, author, parent=None, issue_type=None):
    issue = Issue(name=name, project=project, workspace=workspace, parent=parent, type=issue_type)
    issue.save(created_by_id=author.id)
    return issue


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Hierarchy", identifier="HI", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def other_project(db, workspace, create_user):
    project = Project.objects.create(name="Other", identifier="OT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def epic_type(db, workspace, project):
    issue_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True, level=1)
    ProjectIssueType.objects.create(project=project, issue_type=issue_type, level=1, workspace=workspace)
    return issue_type


@pytest.fixture
def task_type(db, workspace, project):
    issue_type = IssueType.objects.create(workspace=workspace, name="Task", level=0)
    ProjectIssueType.objects.create(project=project, issue_type=issue_type, level=0, workspace=workspace)
    return issue_type


@pytest.mark.contract
class TestParentRules:
    @pytest.mark.django_db
    def test_work_item_cannot_be_its_own_parent(self, session_client, workspace, project, create_user):
        item = _make_issue("Item", project, workspace, create_user)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"parent_id": str(item.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "parent_id" in response.data

    @pytest.mark.django_db
    def test_parent_change_cannot_close_a_cycle(self, session_client, workspace, project, create_user):
        top = _make_issue("Top", project, workspace, create_user)
        middle = _make_issue("Middle", project, workspace, create_user, parent=top)
        bottom = _make_issue("Bottom", project, workspace, create_user, parent=middle)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=top.id),
            {"parent_id": str(bottom.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        top.refresh_from_db()
        assert top.parent_id is None

    @pytest.mark.django_db
    def test_parent_from_another_project_is_rejected(
        self, session_client, workspace, project, other_project, create_user
    ):
        foreign = _make_issue("Foreign", other_project, workspace, create_user)
        item = _make_issue("Item", project, workspace, create_user)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"parent_id": str(foreign.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        item.refresh_from_db()
        assert item.parent_id is None

    @pytest.mark.django_db
    def test_epic_cannot_get_a_parent(self, session_client, workspace, project, epic_type, task_type, create_user):
        parent = _make_issue("Parent", project, workspace, create_user, issue_type=task_type)
        epic = _make_issue("Epic", project, workspace, create_user, issue_type=epic_type)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=epic.id),
            {"parent_id": str(parent.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "parent_id" in response.data

    @pytest.mark.django_db
    def test_type_change_to_epic_is_checked_against_the_current_parent(
        self, session_client, workspace, project, epic_type, task_type, create_user
    ):
        parent = _make_issue("Parent", project, workspace, create_user, issue_type=task_type)
        child = _make_issue("Child", project, workspace, create_user, parent=parent, issue_type=task_type)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=child.id),
            {"type_id": str(epic_type.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        child.refresh_from_db()
        assert child.type_id == task_type.id

    @pytest.mark.django_db
    def test_task_can_be_a_child_of_an_epic(
        self, session_client, workspace, project, epic_type, task_type, create_user
    ):
        epic = _make_issue("Epic", project, workspace, create_user, issue_type=epic_type)
        task = _make_issue("Task", project, workspace, create_user, issue_type=task_type)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=task.id),
            {"parent_id": str(epic.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        task.refresh_from_db()
        assert task.parent_id == epic.id


@pytest.mark.contract
class TestSubIssueAttach:
    @pytest.mark.django_db
    def test_attach_is_all_or_nothing(self, session_client, workspace, project, other_project, create_user):
        parent = _make_issue("Parent", project, workspace, create_user)
        good = _make_issue("Good", project, workspace, create_user)
        foreign = _make_issue("Foreign", other_project, workspace, create_user)
        response = session_client.post(
            SUB_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=parent.id),
            {"sub_issue_ids": [str(good.id), str(foreign.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        good.refresh_from_db()
        assert good.parent_id is None

    @pytest.mark.django_db
    def test_attach_rejects_an_ancestor(self, session_client, workspace, project, create_user):
        top = _make_issue("Top", project, workspace, create_user)
        child = _make_issue("Child", project, workspace, create_user, parent=top)
        response = session_client.post(
            SUB_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=child.id),
            {"sub_issue_ids": [str(top.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        top.refresh_from_db()
        assert top.parent_id is None

    @pytest.mark.django_db
    def test_attach_rejects_an_epic(self, session_client, workspace, project, epic_type, task_type, create_user):
        parent = _make_issue("Parent", project, workspace, create_user, issue_type=task_type)
        epic = _make_issue("Epic", project, workspace, create_user, issue_type=epic_type)
        response = session_client.post(
            SUB_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=parent.id),
            {"sub_issue_ids": [str(epic.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        epic.refresh_from_db()
        assert epic.parent_id is None

    @pytest.mark.django_db
    def test_attach_caps_the_request_size(self, session_client, workspace, project, create_user):
        parent = _make_issue("Parent", project, workspace, create_user)
        ids = ["00000000-0000-0000-0000-%012d" % number for number in range(MAX_SUB_WORK_ITEMS_PER_REQUEST + 1)]
        response = session_client.post(
            SUB_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=parent.id),
            {"sub_issue_ids": ids},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_attach_valid_items(self, session_client, workspace, project, create_user):
        parent = _make_issue("Parent", project, workspace, create_user)
        first = _make_issue("First", project, workspace, create_user)
        second = _make_issue("Second", project, workspace, create_user)
        response = session_client.post(
            SUB_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=parent.id),
            {"sub_issue_ids": [str(first.id), str(second.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert Issue.objects.filter(parent=parent).count() == 2
