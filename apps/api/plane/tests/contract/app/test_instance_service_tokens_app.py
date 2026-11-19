# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bot tokens in God Mode: instance admins create read-only tokens of a service account that sees every project."""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    BotTypeEnum,
    Issue,
    Project,
    ProjectMember,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.license.models import Instance, InstanceAdmin
from plane.utils.service_account import get_service_account

TOKENS = "/api/instances/service-tokens/"


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Test",
        instance_id=uuid4().hex,
        current_version="1.0.0",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


@pytest.fixture
def instance_admin(instance, create_user):
    return InstanceAdmin.objects.create(instance=instance, user=create_user, role=20)


def _project(workspace, name, identifier, network=2):
    return Project.objects.create(name=name, identifier=identifier, workspace=workspace, network=network)


def _api_client(token):
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token)
    return client


def _create(session_client, workspace, **extra):
    payload = {"workspace": str(workspace.id), "label": "Copilot", **extra}
    response = session_client.post(TOKENS, payload, format="json")
    assert response.status_code == 201, response.data
    return response.data


@pytest.mark.contract
@pytest.mark.django_db
class TestServiceTokenAdmin:
    def test_only_instance_admins_manage_bot_tokens(self, session_client, instance, workspace):
        assert session_client.get(TOKENS).status_code == 403
        assert (
            session_client.post(TOKENS, {"workspace": str(workspace.id), "label": "X"}, format="json").status_code
            == 403
        )
        assert not APIToken.objects.exists()

    def test_anonymous_cannot_list(self, api_client, instance):
        assert api_client.get(TOKENS).status_code in (401, 403)

    def test_creates_a_service_account_in_every_project(self, session_client, instance_admin, workspace):
        public = _project(workspace, "Public", "PUB")
        secret = _project(workspace, "Secret", "SEC", network=0)
        other_workspace = Workspace.objects.create(name="Other", slug="other", owner=instance_admin.user)
        elsewhere = _project(other_workspace, "Elsewhere", "ELS")

        data = _create(session_client, workspace, description="For the Graph connector")

        assert data["token"].startswith("plane_api_")
        assert data["token_hint"] == data["token"][-4:]
        assert data["workspace_detail"]["slug"] == workspace.slug
        assert data["project_count"] == 2
        account = get_service_account(workspace.id)
        assert account.is_bot and account.bot_type == BotTypeEnum.SERVICE_ACCOUNT
        assert WorkspaceMember.objects.filter(workspace=workspace, member=account, role=15, is_active=True).exists()
        joined = set(ProjectMember.objects.filter(member=account, is_active=True).values_list("project_id", flat=True))
        assert joined == {public.id, secret.id}
        assert elsewhere.id not in joined
        token = APIToken.objects.get(token=data["token"])
        assert token.user_type == 1 and token.workspace_id == workspace.id

    def test_a_second_token_reuses_the_account(self, session_client, instance_admin, workspace):
        _project(workspace, "Public", "PUB")
        first = _create(session_client, workspace)
        second = _create(session_client, workspace, label="MCP")
        assert first["token"] != second["token"]
        assert User.objects.filter(is_bot=True, bot_type=BotTypeEnum.SERVICE_ACCOUNT).count() == 1
        assert ProjectMember.objects.filter(member=get_service_account(workspace.id)).count() == 1

    def test_list_never_shows_the_token(self, session_client, instance_admin, workspace):
        created = _create(session_client, workspace)
        # an ordinary personal token is not a bot token
        APIToken.objects.create(user=instance_admin.user, label="Personal")
        response = session_client.get(TOKENS)
        assert response.status_code == 200
        assert [row["id"] for row in response.data] == [created["id"]]
        assert "token" not in response.data[0]
        assert response.data[0]["created_by_detail"]["email"] == instance_admin.user.email

    def test_validates_the_request(self, session_client, instance_admin, workspace):
        assert session_client.post(TOKENS, {"label": "X"}, format="json").status_code == 400
        assert session_client.post(TOKENS, {"workspace": str(uuid4()), "label": "X"}, format="json").status_code == 400
        assert (
            session_client.post(TOKENS, {"workspace": str(workspace.id), "label": " "}, format="json").status_code
            == 400
        )
        past = (timezone.now() - timedelta(days=1)).isoformat()
        response = session_client.post(
            TOKENS, {"workspace": str(workspace.id), "label": "X", "expired_at": past}, format="json"
        )
        assert response.status_code == 400
        assert response.data == {"error": "expired_at must be in the future"}
        for wrong in ("tomorrow", "2027-02-30", "2027-13-01T10:00:00"):
            response = session_client.post(
                TOKENS, {"workspace": str(workspace.id), "label": "X", "expired_at": wrong}, format="json"
            )
            assert response.status_code == 400, wrong
            assert response.data == {"error": "expired_at must be an ISO date or date-time"}
        assert not APIToken.objects.exists()

    def test_accepts_a_workspace_slug_and_an_expiry_date(self, session_client, instance_admin, workspace):
        day = (timezone.now() + timedelta(days=30)).date().isoformat()
        response = session_client.post(
            TOKENS, {"workspace": workspace.slug, "label": "Copilot", "expired_at": day}, format="json"
        )
        assert response.status_code == 201, response.data
        data = response.data
        assert data["expired_at"] is not None
        assert data["is_expired"] is False

    def test_revoking_stops_the_token(self, session_client, instance_admin, workspace):
        data = _create(session_client, workspace)
        client = _api_client(data["token"])
        assert client.get(f"/api/v1/workspaces/{workspace.slug}/projects/").status_code == 200

        assert session_client.delete(f"{TOKENS}{data['id']}/").status_code == 204
        # an unknown token is rejected (DRF answers 403 for API-key auth, which has no WWW-Authenticate challenge)
        assert client.get(f"/api/v1/workspaces/{workspace.slug}/projects/").status_code in (401, 403)
        assert not APIToken.objects.filter(token=data["token"]).exists()
        assert session_client.get(TOKENS).data == []

    def test_cannot_revoke_a_personal_token_here(self, session_client, instance_admin):
        personal = APIToken.objects.create(user=instance_admin.user, label="Personal")
        assert session_client.delete(f"{TOKENS}{personal.id}/").status_code == 404
        assert APIToken.objects.filter(pk=personal.pk, is_active=True).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestServiceTokenAccess:
    def test_reads_every_project_and_its_work_items(self, session_client, instance_admin, workspace):
        public = _project(workspace, "Public", "PUB")
        secret = _project(workspace, "Secret", "SEC", network=0)
        issue = Issue.objects.create(name="Montaż obudowy", project=secret, workspace=workspace)
        client = _api_client(_create(session_client, workspace)["token"])

        projects = client.get(f"/api/v1/workspaces/{workspace.slug}/projects/")
        assert projects.status_code == 200
        listed = projects.data["results"] if isinstance(projects.data, dict) else projects.data
        assert {str(row["id"]) for row in listed} >= {str(public.id), str(secret.id)}

        items = client.get(f"/api/v1/workspaces/{workspace.slug}/projects/{secret.id}/work-items/")
        assert items.status_code == 200, items.data
        assert [str(row["id"]) for row in items.data["results"]] == [str(issue.id)]
        for path in ("states", "members"):
            response = client.get(f"/api/v1/workspaces/{workspace.slug}/projects/{secret.id}/{path}/")
            assert response.status_code == 200, (path, response.data)

    def test_a_project_created_later_is_visible_too(self, session_client, instance_admin, workspace):
        client = _api_client(_create(session_client, workspace)["token"])
        later = _project(workspace, "Later", "LAT", network=0)
        assert ProjectMember.objects.filter(
            project=later, member=get_service_account(workspace.id), is_active=True
        ).exists()
        response = client.get(f"/api/v1/workspaces/{workspace.slug}/projects/{later.id}/work-items/")
        assert response.status_code == 200, response.data

    def test_projects_of_other_workspaces_get_no_service_account(self, session_client, instance_admin, workspace):
        _create(session_client, workspace)
        other_workspace = Workspace.objects.create(name="Other", slug="other", owner=instance_admin.user)
        other = _project(other_workspace, "Elsewhere", "ELS")
        assert not ProjectMember.objects.filter(project=other, member__is_bot=True).exists()

    def test_the_token_is_read_only(self, session_client, instance_admin, workspace):
        project = _project(workspace, "Public", "PUB")
        client = _api_client(_create(session_client, workspace)["token"])
        base = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}"

        response = client.post(f"{base}/work-items/", {"name": "Should not exist"}, format="json")
        assert response.status_code == 403
        assert "read-only" in str(response.data)
        assert client.patch(f"{base}/", {"name": "Renamed"}, format="json").status_code == 403
        assert client.delete(f"{base}/").status_code == 403
        assert not Issue.objects.filter(name="Should not exist").exists()
        project.refresh_from_db()
        assert project.name == "Public" and project.deleted_at is None

    def test_personal_tokens_of_people_keep_writing(self, workspace, create_user):
        """The read-only rule is for the service account only."""
        project = _project(workspace, "Public", "PUB")
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        client = _api_client(APIToken.objects.create(user=create_user, label="Personal").token)
        response = client.post(
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/", {"name": "Fine"}, format="json"
        )
        assert response.status_code == 201, response.data
