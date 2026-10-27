# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests: sharing a project on the web is for project admins.

The web app shows the "Share on the web" menu item to project admins only. ``DeployBoardViewSet`` uses
``ProjectMemberPermission``, which lets project members write too, so a member could switch sharing on, change it or
switch it off through the API.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import DeployBoard, Project, ProjectMember, User, WorkspaceMember


def board_url(slug, project_id, pk=None):
    base = f"/api/workspaces/{slug}/projects/{project_id}/project-deploy-boards/"
    return f"{base}{pk}/" if pk else base


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Shared", identifier="SH", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


def client_with_role(workspace, project, role):
    unique = uuid4().hex[:8]
    user = User.objects.create(email=f"u-{unique}@plane.so", username=f"u_{unique}")
    user.set_password("test-password")
    user.save()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15 if role != 5 else 5)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role, is_active=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.contract
class TestDeployBoardAdminOnly:
    @pytest.mark.django_db
    @pytest.mark.parametrize("role", [15, 5])
    def test_member_and_guest_cannot_turn_sharing_on(self, workspace, project, role):
        client = client_with_role(workspace, project, role)
        response = client.post(board_url(workspace.slug, project.id), {"views": {"list": True}}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
        assert not DeployBoard.objects.filter(project=project).exists()

    @pytest.mark.django_db
    def test_member_cannot_change_or_stop_sharing(self, workspace, project, session_client):
        created = session_client.post(board_url(workspace.slug, project.id), {"views": {"list": True}}, format="json")
        assert created.status_code == status.HTTP_200_OK, created.data
        board_id = created.data["id"]
        member = client_with_role(workspace, project, 15)

        patch = member.patch(
            board_url(workspace.slug, project.id, board_id), {"is_comments_enabled": True}, format="json"
        )
        assert patch.status_code == status.HTTP_403_FORBIDDEN, patch.data
        delete = member.delete(board_url(workspace.slug, project.id, board_id))
        assert delete.status_code == status.HTTP_403_FORBIDDEN
        assert DeployBoard.objects.filter(pk=board_id, is_comments_enabled=False).exists()

    @pytest.mark.django_db
    def test_project_admin_can_share_change_and_stop(self, workspace, project, session_client):
        """``create_user`` is a project admin."""
        created = session_client.post(board_url(workspace.slug, project.id), {"views": {"list": True}}, format="json")
        assert created.status_code == status.HTTP_200_OK, created.data
        board_id = created.data["id"]
        patched = session_client.patch(
            board_url(workspace.slug, project.id, board_id), {"is_comments_enabled": True}, format="json"
        )
        assert patched.status_code == status.HTTP_200_OK, patched.data
        assert DeployBoard.objects.get(pk=board_id).is_comments_enabled is True
        deleted = session_client.delete(board_url(workspace.slug, project.id, board_id))
        assert deleted.status_code == status.HTTP_204_NO_CONTENT
        assert not DeployBoard.objects.filter(pk=board_id).exists()

    @pytest.mark.django_db
    def test_member_can_still_read_the_sharing_settings(self, workspace, project, session_client):
        session_client.post(board_url(workspace.slug, project.id), {"views": {"list": True}}, format="json")
        member = client_with_role(workspace, project, 15)
        response = member.get(board_url(workspace.slug, project.id))
        assert response.status_code == status.HTTP_200_OK
