# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the per-project Epics switch.

Epics are on in a project when an `is_epic` work item type is linked to it. Switching them off keeps the existing
Epics and their children, and only stops new Epics.
"""

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueType, Project, ProjectIssueType, ProjectMember, User, WorkspaceMember

EPICS_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-types/epics/"
ISSUE_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
ISSUE_TYPE_URL = "/api/workspaces/{slug}/issue-types/{pk}/"


def _make_issue(name, project, workspace, author, parent=None, issue_type=None):
    issue = Issue(name=name, project=project, workspace=workspace, parent=parent, type=issue_type)
    issue.save(created_by_id=author.id)
    return issue


def _linked(project, **filters):
    return ProjectIssueType.objects.filter(project=project, deleted_at__isnull=True, **filters)


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Epics", identifier="EP", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def task_type(db, workspace, project):
    issue_type = IssueType.objects.create(workspace=workspace, name="Task", is_default=True)
    ProjectIssueType.objects.create(project=project, issue_type=issue_type, workspace=workspace, is_default=True)
    return issue_type


def _member_client(api_client, workspace, project, role, email):
    user = User.objects.create(email=email, username=email, first_name="M", last_name="M")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role)
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.contract
class TestEpicsSwitch:
    @pytest.mark.django_db
    def test_turning_on_creates_and_links_the_epic_type(self, session_client, workspace, project, task_type):
        response = session_client.post(EPICS_URL.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["is_epic"] is True
        epic = IssueType.objects.get(workspace=workspace, is_epic=True)
        assert _linked(project, issue_type=epic).exists()

    @pytest.mark.django_db
    def test_turning_on_twice_changes_nothing(self, session_client, workspace, project, task_type):
        url = EPICS_URL.format(slug=workspace.slug, project_id=project.id)
        session_client.post(url)
        session_client.post(url)
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1
        assert _linked(project, issue_type__is_epic=True).count() == 1

    @pytest.mark.django_db
    def test_needs_work_item_types_to_be_enabled(self, session_client, workspace, project):
        project.is_issue_type_enabled = False
        project.save()
        response = session_client.post(EPICS_URL.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not IssueType.objects.filter(workspace=workspace, is_epic=True).exists()

    @pytest.mark.django_db
    def test_uses_the_oldest_epic_type_of_the_workspace(self, session_client, workspace, project, task_type):
        oldest = IssueType.objects.create(workspace=workspace, name="Big rock", is_epic=True)
        IssueType.objects.create(workspace=workspace, name="Another", is_epic=True)
        response = session_client.post(EPICS_URL.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data["id"]) == str(oldest.id)
        assert _linked(project, issue_type__is_epic=True).count() == 1

    @pytest.mark.django_db
    def test_a_non_epic_type_named_epic_does_not_clash(self, session_client, workspace, project, task_type):
        IssueType.objects.create(workspace=workspace, name="Epic", is_epic=False)
        response = session_client.post(EPICS_URL.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_epic"] is True
        assert response.data["name"] != "Epic"

    @pytest.mark.django_db
    def test_turning_off_unlinks_every_epic_type_of_the_project(self, session_client, workspace, project, task_type):
        second = IssueType.objects.create(workspace=workspace, name="Another", is_epic=True)
        ProjectIssueType.objects.create(project=project, issue_type=second, workspace=workspace)
        url = EPICS_URL.format(slug=workspace.slug, project_id=project.id)
        session_client.post(url)
        response = session_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not _linked(project, issue_type__is_epic=True).exists()
        assert _linked(project, issue_type=task_type).exists()

    @pytest.mark.django_db
    def test_off_keeps_existing_epics_and_on_again_restores_them(
        self, session_client, workspace, project, task_type, create_user
    ):
        url = EPICS_URL.format(slug=workspace.slug, project_id=project.id)
        epic_type = IssueType.objects.get(pk=session_client.post(url).data["id"])
        epic = _make_issue("Epic", project, workspace, create_user, issue_type=epic_type)
        child = _make_issue("Child", project, workspace, create_user, parent=epic, issue_type=task_type)

        session_client.delete(url)

        epic.refresh_from_db()
        child.refresh_from_db()
        assert epic.type_id == epic_type.id
        assert child.parent_id == epic.id
        # An Epic stays editable while Epics are off, because it keeps the type it has
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=epic.id),
            {"name": "Epic renamed", "type_id": str(epic_type.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        # but nothing can become an Epic
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=child.id),
            {"type_id": str(epic_type.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        again = session_client.post(url)
        assert again.status_code == status.HTTP_200_OK
        assert str(again.data["id"]) == str(epic_type.id)
        epic.refresh_from_db()
        assert epic.type_id == epic_type.id
        assert Issue.objects.get(pk=child.pk).parent_id == epic.id

    @pytest.mark.django_db
    def test_only_project_admins_can_switch(self, api_client, workspace, project, task_type):
        url = EPICS_URL.format(slug=workspace.slug, project_id=project.id)
        member_client = _member_client(api_client, workspace, project, 15, "member@example.com")
        assert member_client.post(url).status_code == status.HTTP_403_FORBIDDEN
        assert member_client.delete(url).status_code == status.HTTP_403_FORBIDDEN
        guest_client = _member_client(api_client, workspace, project, 5, "guest@example.com")
        assert guest_client.post(url).status_code == status.HTTP_403_FORBIDDEN
        assert not IssueType.objects.filter(workspace=workspace, is_epic=True).exists()


@pytest.mark.contract
class TestIsEpicFlag:
    @pytest.mark.django_db
    def test_flag_cannot_change_while_a_work_item_uses_the_type(
        self, session_client, workspace, project, task_type, create_user
    ):
        _make_issue("Task", project, workspace, create_user, issue_type=task_type)
        response = session_client.patch(
            ISSUE_TYPE_URL.format(slug=workspace.slug, pk=task_type.id), {"is_epic": True}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        task_type.refresh_from_db()
        assert task_type.is_epic is False

    @pytest.mark.django_db
    def test_flag_can_change_on_an_unused_type(self, session_client, workspace, project, task_type):
        response = session_client.patch(
            ISSUE_TYPE_URL.format(slug=workspace.slug, pk=task_type.id), {"is_epic": True}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        task_type.refresh_from_db()
        assert task_type.is_epic is True

    @pytest.mark.django_db
    def test_saving_the_same_flag_on_a_used_type_is_fine(
        self, session_client, workspace, project, task_type, create_user
    ):
        _make_issue("Task", project, workspace, create_user, issue_type=task_type)
        response = session_client.patch(
            ISSUE_TYPE_URL.format(slug=workspace.slug, pk=task_type.id),
            {"is_epic": False, "description": "x"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data


@pytest.mark.contract
class TestTypeAssignment:
    @pytest.mark.django_db
    def test_type_is_refused_when_types_are_off_in_the_project(
        self, session_client, workspace, project, task_type, create_user
    ):
        project.is_issue_type_enabled = False
        project.save()
        item = _make_issue("Item", project, workspace, create_user)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"type_id": str(task_type.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_public_api_refuses_a_type_that_is_not_linked(self, workspace, project, task_type, create_user):
        from plane.api.serializers import IssueSerializer

        other = IssueType.objects.create(workspace=workspace, name="Unlinked")
        serializer = IssueSerializer(
            data={"name": "X", "type_id": str(other.id)},
            context={"project_id": project.id, "workspace_id": workspace.id, "default_assignee_id": None},
        )
        assert not serializer.is_valid()
        assert "type_id" in serializer.errors
