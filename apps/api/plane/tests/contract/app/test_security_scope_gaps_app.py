# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

"""Contract tests for three authorization gaps still present upstream.

* Project member preferences (CVE-2026-102985): ``member_id`` in the URL was never
  compared to the caller, so any project member could read or rewrite another
  member's preferences. Now only the owner, a project admin or a workspace admin may.
* Public Spaces asset upload (CVE-2026-102986): any authenticated user who knew a
  board anchor could create assets of any entity type in the board's project, and
  attach them to any ``comment_id``. Now limited to the entity types the Spaces client
  uses, only on boards with comments enabled, and the comment must be in the board's
  project.
* Issue modules endpoint (CVE-2026-104894): the URL ``issue_id`` and the body
  ``modules`` ids were written unscoped. Now bound to the URL workspace + project.
"""

from unittest import mock
from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    DeployBoard,
    FileAsset,
    Issue,
    IssueComment,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)


def preference_url(slug, project_id, member_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/preferences/member/{member_id}/"


def issue_modules_url(slug, project_id, issue_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/modules/"


def asset_url(anchor):
    return f"/api/public/assets/v2/anchor/{anchor}/"


def make_user(prefix):
    unique_id = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unique_id}@plane.so",
        username=f"{prefix}_{unique_id}",
        first_name=prefix,
        last_name="User",
    )
    user.set_password("test-password")
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Scope Project", identifier="SCP", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20, is_active=True)
    return project


@pytest.fixture
def make_member(db, workspace, project):
    """Create a workspace member with the given project role; returns (user, client)."""

    def _make(prefix, role):
        user = make_user(prefix)
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
        ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role, is_active=True)
        return user, client_for(user)

    return _make


@pytest.mark.contract
class TestProjectMemberPreferenceOwnership:
    @pytest.mark.django_db
    def test_member_cannot_patch_other_members_preferences(self, workspace, project, make_member):
        _, attacker = make_member("attacker", 15)
        victim, _ = make_member("victim", 15)
        response = attacker.patch(
            preference_url(workspace.slug, project.id, victim.id), {"navigation": {}}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    @pytest.mark.django_db
    def test_guest_cannot_read_other_members_preferences(self, workspace, project, make_member):
        _, guest = make_member("guest", 5)
        victim, _ = make_member("victim", 15)
        response = guest.get(preference_url(workspace.slug, project.id, victim.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    @pytest.mark.django_db
    def test_member_can_use_own_preferences(self, workspace, project, make_member):
        user, client = make_member("owner", 15)
        response = client.get(preference_url(workspace.slug, project.id, user.id))
        assert response.status_code == status.HTTP_200_OK, response.data

    @pytest.mark.django_db
    def test_project_admin_keeps_edit_rights(self, workspace, project, make_member):
        _, admin = make_member("padmin", 20)
        victim, _ = make_member("victim", 15)
        assert admin.get(preference_url(workspace.slug, project.id, victim.id)).status_code == status.HTTP_200_OK
        response = admin.patch(preference_url(workspace.slug, project.id, victim.id), {}, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data

    @pytest.mark.django_db
    def test_workspace_admin_keeps_edit_rights(self, workspace, project, make_member, session_client):
        """``create_user`` is a workspace admin (and project admin)."""
        victim, _ = make_member("victim", 15)
        response = session_client.patch(preference_url(workspace.slug, project.id, victim.id), {}, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data


@pytest.fixture
def visitor(db):
    return make_user("visitor")


@pytest.fixture
def board(db, workspace, project, create_user, visitor):
    state = State.objects.create(name="Todo", project=project, workspace=workspace, group="backlog", default=True)
    issue = Issue.objects.create(
        name="Issue", workspace=workspace, project=project, state=state, created_by=create_user
    )
    comment = IssueComment.objects.create(
        issue=issue,
        project=project,
        workspace=workspace,
        comment_html="<p>c</p>",
        access="EXTERNAL",
        created_by=visitor,
        actor=visitor,
    )
    deploy_board = DeployBoard.objects.create(
        entity_name="project",
        entity_identifier=project.id,
        project=project,
        workspace=workspace,
        is_comments_enabled=True,
    )
    return {"board": deploy_board, "anchor": deploy_board.anchor, "comment": comment, "issue": issue}


@pytest.fixture
def visitor_client(visitor):
    return client_for(visitor)


@pytest.fixture(autouse=True)
def _no_storage(db):
    with mock.patch("plane.space.views.asset.S3Storage") as storage:
        storage.return_value.generate_presigned_post.return_value = {"url": "https://s3.test", "fields": {}}
        yield


def upload_payload(**overrides):
    payload = {"name": "a.png", "type": "image/png", "size": 10, "entity_type": "COMMENT_DESCRIPTION"}
    payload.update(overrides)
    return payload


@pytest.mark.contract
class TestPublicAssetUploadScope:
    @pytest.mark.django_db
    def test_comment_upload_allowed_on_comment_enabled_board(self, visitor_client, board):
        payload = upload_payload(entity_identifier=str(board["comment"].id))
        response = visitor_client.post(asset_url(board["anchor"]), payload, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert FileAsset.objects.get(pk=response.data["asset_id"]).comment_id == board["comment"].id

    @pytest.mark.django_db
    def test_upload_without_comment_id_allowed(self, visitor_client, board):
        response = visitor_client.post(asset_url(board["anchor"]), upload_payload(entity_identifier=""), format="json")
        assert response.status_code == status.HTTP_200_OK, response.data

    @pytest.mark.django_db
    def test_other_entity_types_rejected(self, visitor_client, board):
        before = FileAsset.objects.count()
        response = visitor_client.post(
            asset_url(board["anchor"]), upload_payload(entity_type="USER_AVATAR"), format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert FileAsset.objects.count() == before

    @pytest.mark.django_db
    def test_rejected_when_comments_disabled(self, visitor_client, board):
        DeployBoard.objects.filter(pk=board["board"].pk).update(is_comments_enabled=False)
        before = FileAsset.objects.count()
        response = visitor_client.post(asset_url(board["anchor"]), upload_payload(), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert FileAsset.objects.count() == before

    @pytest.mark.django_db
    def test_comment_from_another_project_rejected(self, visitor_client, board, workspace, create_user):
        other = Project.objects.create(name="Other", identifier="OTH", workspace=workspace, created_by=create_user)
        state = State.objects.create(name="Todo", project=other, workspace=workspace, group="backlog", default=True)
        issue = Issue.objects.create(name="X", workspace=workspace, project=other, state=state, created_by=create_user)
        foreign = IssueComment.objects.create(
            issue=issue, project=other, workspace=workspace, comment_html="<p>f</p>", actor=create_user
        )
        before = FileAsset.objects.count()
        response = visitor_client.post(
            asset_url(board["anchor"]), upload_payload(entity_identifier=str(foreign.id)), format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert FileAsset.objects.count() == before

    @pytest.mark.django_db
    def test_malformed_comment_id_rejected(self, visitor_client, board):
        response = visitor_client.post(
            asset_url(board["anchor"]), upload_payload(entity_identifier="not-a-uuid"), format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.fixture(autouse=False)
def _no_activity():
    with mock.patch("plane.app.views.module.issue.issue_activity"):
        yield


@pytest.mark.contract
class TestIssueModulesScope:
    @pytest.fixture
    def setup(self, db, workspace, project, create_user, board):
        module = Module.objects.create(name="M", project=project, workspace=workspace)
        other = Project.objects.create(name="Other", identifier="OTH", workspace=workspace, created_by=create_user)
        state = State.objects.create(name="Todo", project=other, workspace=workspace, group="backlog", default=True)
        foreign_issue = Issue.objects.create(
            name="Foreign", workspace=workspace, project=other, state=state, created_by=create_user
        )
        foreign_module = Module.objects.create(name="FM", project=other, workspace=workspace)
        return {"module": module, "foreign_issue": foreign_issue, "foreign_module": foreign_module}

    @pytest.mark.django_db
    def test_own_issue_and_module_link(self, _no_activity, session_client, workspace, project, board, setup):
        response = session_client.post(
            issue_modules_url(workspace.slug, project.id, board["issue"].id),
            {"modules": [str(setup["module"].id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert ModuleIssue.objects.filter(issue=board["issue"], module=setup["module"]).count() == 1

    @pytest.mark.django_db
    def test_foreign_issue_in_url_rejected(self, _no_activity, session_client, workspace, project, setup):
        response = session_client.post(
            issue_modules_url(workspace.slug, project.id, setup["foreign_issue"].id),
            {"modules": []},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_foreign_module_ignored(self, _no_activity, session_client, workspace, project, board, setup):
        response = session_client.post(
            issue_modules_url(workspace.slug, project.id, board["issue"].id),
            {"modules": [str(setup["foreign_module"].id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert not ModuleIssue.objects.filter(module=setup["foreign_module"]).exists()
