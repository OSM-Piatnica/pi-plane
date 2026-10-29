# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Turning Space (the public sharing site) off: by the instance admin, or by leaving it out of the deployment."""

from uuid import uuid4

import pytest
from django.core.cache import cache
from django.utils import timezone

from plane.db.models import DeployBoard, Project, ProjectMember
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration

KEY = "IS_SPACE_ENABLED"
CONFIGURATIONS = "/api/instances/configurations/"
INSTANCE = "/api/instances/"
OFF_MESSAGE = "Web sharing is turned off on this instance."


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def deployed(monkeypatch):
    monkeypatch.delenv("ENABLE_SPACE", raising=False)


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


@pytest.fixture
def setting(db):
    return InstanceConfiguration.objects.create(key=KEY, value="1", category="WORKSPACE_MANAGEMENT")


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Shared", identifier="SH", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


def board_url(workspace, project):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/project-deploy-boards/"


def turn_off(setting):
    setting.value = "0"
    setting.save()
    cache.clear()


def public_url(anchor="no-such-board"):
    return f"/api/public/anchor/{anchor}/meta/"


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicApi:
    def test_the_public_api_answers_while_space_is_on(self, api_client, setting):
        response = api_client.get(public_url())

        # an unknown board, not a refusal of the whole site
        assert response.status_code == 404
        assert response.json().get("error") != OFF_MESSAGE

    def test_the_public_api_is_refused_while_space_is_off(self, api_client, setting):
        turn_off(setting)

        response = api_client.get(public_url())

        assert response.status_code == 404
        assert response.json() == {"error": OFF_MESSAGE}

    def test_the_sign_in_of_the_public_site_is_refused_while_space_is_off(self, api_client, setting):
        turn_off(setting)

        response = api_client.post("/auth/spaces/sign-in/", {}, format="json")

        assert response.status_code == 404
        assert response.json() == {"error": OFF_MESSAGE}

    def test_a_board_that_was_shared_before_is_not_served_but_stays_stored(
        self, api_client, setting, workspace, project
    ):
        board = DeployBoard.objects.create(
            entity_name="project", entity_identifier=project.id, project=project, workspace=workspace
        )
        turn_off(setting)

        assert api_client.get(public_url(board.anchor)).json() == {"error": OFF_MESSAGE}
        assert DeployBoard.objects.filter(pk=board.pk).exists()

        setting.value = "1"
        setting.save()
        assert api_client.get(public_url(board.anchor)).json().get("error") != OFF_MESSAGE

    def test_leaving_space_out_of_the_deployment_turns_it_off_whatever_the_admin_chose(
        self, api_client, setting, monkeypatch
    ):
        monkeypatch.setenv("ENABLE_SPACE", "0")

        assert setting.value == "1"
        assert api_client.get(public_url()).json() == {"error": OFF_MESSAGE}

    def test_a_missing_setting_means_on(self, api_client, db):
        assert api_client.get(public_url()).json().get("error") != OFF_MESSAGE


@pytest.mark.contract
@pytest.mark.django_db
class TestPublishing:
    def test_a_project_admin_can_share_while_space_is_on(self, session_client, setting, workspace, project):
        response = session_client.post(board_url(workspace, project), {"views": {"list": True}}, format="json")

        assert response.status_code == 200, response.data
        assert DeployBoard.objects.filter(project=project).exists()

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_sharing_is_refused_while_space_is_off(self, session_client, setting, workspace, project, method):
        turn_off(setting)

        response = getattr(session_client, method)(board_url(workspace, project), {"views": {}}, format="json")

        assert response.status_code == 403
        assert OFF_MESSAGE in str(response.data)
        assert not DeployBoard.objects.filter(project=project).exists()

    def test_changing_or_stopping_a_board_is_refused_while_space_is_off(
        self, session_client, setting, workspace, project
    ):
        board = DeployBoard.objects.create(
            entity_name="project", entity_identifier=project.id, project=project, workspace=workspace
        )
        turn_off(setting)
        url = f"{board_url(workspace, project)}{board.id}/"

        assert session_client.patch(url, {"is_comments_enabled": True}, format="json").status_code == 403
        assert session_client.delete(url).status_code == 403
        assert DeployBoard.objects.filter(pk=board.pk).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestAdminSetting:
    def test_the_instance_config_tells_the_apps_whether_sharing_is_on(self, api_client, instance, setting):
        on = api_client.get(INSTANCE).data["config"]
        turn_off(setting)
        off = api_client.get(INSTANCE).data["config"]

        assert (on["is_space_enabled"], on["is_space_deployed"]) == (True, True)
        assert (off["is_space_enabled"], off["is_space_deployed"]) == (False, True)

    def test_an_instance_admin_turns_it_off_and_on_again(self, session_client, instance_admin, setting, api_client):
        assert session_client.patch(CONFIGURATIONS, {KEY: "0"}, format="json").status_code == 200
        assert api_client.get(INSTANCE).data["config"]["is_space_enabled"] is False

        assert session_client.patch(CONFIGURATIONS, {KEY: "1"}, format="json").status_code == 200
        assert api_client.get(INSTANCE).data["config"]["is_space_enabled"] is True

    def test_only_an_instance_admin_can_change_it(self, session_client, instance, setting):
        response = session_client.patch(CONFIGURATIONS, {KEY: "0"}, format="json")

        assert response.status_code == 403
        setting.refresh_from_db()
        assert setting.value == "1"

    def test_a_deployment_without_space_reports_it_whatever_the_setting_says(
        self, api_client, instance, setting, monkeypatch
    ):
        monkeypatch.setenv("ENABLE_SPACE", "0")

        config = api_client.get(INSTANCE).data["config"]

        assert (config["is_space_enabled"], config["is_space_deployed"]) == (False, False)
