# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for a user's app preferences in a workspace: the default app, and the order and hidden state of
the rail apps.

Only the Projects app exists, so the tests that need a second app add ``approvals`` to the known keys for their own
duration.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import User, WorkspaceMember, WorkspaceUserPreference, WorkspaceUserProperties
from plane.utils import app_rail
from plane.utils.app_rail import APP_RAIL_APP_KEYS

PROPERTIES_URL = "/api/workspaces/{slug}/user-properties/"
PREFERENCES_URL = "/api/workspaces/{slug}/sidebar-preferences/"


def _member(workspace, role):
    unique = uuid4().hex[:8]
    user = User.objects.create(email=f"app-{role}-{unique}@plane.so", username=f"app_{role}_{unique}")
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=role, is_active=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


@pytest.fixture
def two_apps(monkeypatch):
    monkeypatch.setattr(app_rail, "APP_RAIL_APP_KEYS", ("projects", "approvals"))


@pytest.mark.contract
@pytest.mark.django_db
class TestDefaultApp:
    def test_projects_and_initiatives_are_known(self):
        assert APP_RAIL_APP_KEYS == ("projects", "initiatives")

    def test_initiatives_is_accepted(self, session_client, workspace):
        response = session_client.patch(
            PROPERTIES_URL.format(slug=workspace.slug), {"default_app": "initiatives"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["default_app"] == "initiatives"

    def test_default_is_null(self, session_client, workspace):
        response = session_client.get(PROPERTIES_URL.format(slug=workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["default_app"] is None

    @pytest.mark.parametrize("role", [20, 15, 5])
    def test_every_member_sets_and_clears_their_own(self, workspace, role):
        user, client = _member(workspace, role)
        url = PROPERTIES_URL.format(slug=workspace.slug)

        response = client.patch(url, {"default_app": "projects"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["default_app"] == "projects"
        assert client.get(url).data["default_app"] == "projects"

        response = client.patch(url, {"default_app": None}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert WorkspaceUserProperties.objects.get(workspace=workspace, user=user).default_app is None

    @pytest.mark.parametrize("value", ["approvals", "unknown", "", 5, ["projects"]])
    def test_unknown_app_is_rejected(self, session_client, workspace, create_user, value):
        response = session_client.patch(
            PROPERTIES_URL.format(slug=workspace.slug), {"default_app": value}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "default_app" in response.data
        properties = WorkspaceUserProperties.objects.filter(workspace=workspace, user=create_user).first()
        assert properties is None or properties.default_app is None

    @pytest.mark.usefixtures("two_apps")
    def test_a_registered_second_app_is_accepted(self, session_client, workspace):
        response = session_client.patch(
            PROPERTIES_URL.format(slug=workspace.slug), {"default_app": "approvals"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["default_app"] == "approvals"

    def test_setting_it_keeps_the_other_properties(self, session_client, workspace, create_user):
        url = PROPERTIES_URL.format(slug=workspace.slug)
        session_client.patch(url, {"navigation_project_limit": 7}, format="json")

        session_client.patch(url, {"default_app": "projects"}, format="json")

        properties = WorkspaceUserProperties.objects.get(workspace=workspace, user=create_user)
        assert properties.navigation_project_limit == 7
        assert properties.default_app == "projects"

    def test_it_is_personal(self, session_client, workspace):
        other, other_client = _member(workspace, 15)
        url = PROPERTIES_URL.format(slug=workspace.slug)

        session_client.patch(url, {"default_app": "projects"}, format="json")

        assert other_client.get(url).data["default_app"] is None
        # the owner of the row cannot be redirected through the payload
        other_client.patch(url, {"default_app": "projects", "user": str(other.id)}, format="json")
        assert WorkspaceUserProperties.objects.filter(workspace=workspace, default_app="projects").count() == 2

    def test_non_member_cannot_set(self, workspace):
        _, client = _member(None, 20)

        response = client.patch(PROPERTIES_URL.format(slug=workspace.slug), {"default_app": "projects"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not WorkspaceUserProperties.objects.filter(workspace=workspace, default_app="projects").exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestAppRailPreferences:
    def test_reading_creates_no_row_for_an_app(self, session_client, workspace):
        response = session_client.get(PREFERENCES_URL.format(slug=workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert not [key for key in response.data if key.startswith("app_rail:")]

    @pytest.mark.parametrize("role", [20, 15, 5])
    def test_order_and_hidden_state_are_stored_on_first_write(self, workspace, role):
        user, client = _member(workspace, role)
        url = PREFERENCES_URL.format(slug=workspace.slug)

        response = client.patch(url, [{"key": "app_rail:projects", "is_pinned": False, "sort_order": 2}], format="json")

        assert response.status_code == status.HTTP_200_OK
        assert client.get(url).data["app_rail:projects"] == {"is_pinned": False, "sort_order": 2}

        client.patch(url, [{"key": "app_rail:projects", "is_pinned": True, "sort_order": 1}], format="json")

        assert client.get(url).data["app_rail:projects"] == {"is_pinned": True, "sort_order": 1}
        assert (
            WorkspaceUserPreference.objects.filter(workspace=workspace, user=user, key="app_rail:projects").count() == 1
        )

    def test_an_app_is_shown_unless_hidden(self, session_client, workspace):
        url = PREFERENCES_URL.format(slug=workspace.slug)

        session_client.patch(url, [{"key": "app_rail:projects", "sort_order": 3}], format="json")

        assert session_client.get(url).data["app_rail:projects"] == {"is_pinned": True, "sort_order": 3}

    @pytest.mark.parametrize("key", ["app_rail:approvals", "app_rail:", "app_rail", "projects", "anything_else"])
    def test_unknown_keys_are_ignored(self, session_client, workspace, key):
        url = PREFERENCES_URL.format(slug=workspace.slug)

        response = session_client.patch(url, [{"key": key, "is_pinned": True, "sort_order": 1}], format="json")

        assert response.status_code == status.HTTP_200_OK
        assert not WorkspaceUserPreference.objects.filter(workspace=workspace, key=key).exists()

    @pytest.mark.usefixtures("two_apps")
    def test_two_apps_are_ordered(self, session_client, workspace):
        url = PREFERENCES_URL.format(slug=workspace.slug)

        session_client.patch(
            url,
            [
                {"key": "app_rail:projects", "is_pinned": True, "sort_order": 1},
                {"key": "app_rail:approvals", "is_pinned": True, "sort_order": 0},
            ],
            format="json",
        )

        data = session_client.get(url).data
        assert [key for key in data if key.startswith("app_rail:")] == ["app_rail:approvals", "app_rail:projects"]

    def test_it_is_personal(self, session_client, workspace):
        _, other_client = _member(workspace, 15)
        url = PREFERENCES_URL.format(slug=workspace.slug)

        session_client.patch(url, [{"key": "app_rail:projects", "is_pinned": False, "sort_order": 4}], format="json")

        assert "app_rail:projects" not in other_client.get(url).data

    def test_the_sidebar_items_keep_working(self, session_client, workspace):
        url = PREFERENCES_URL.format(slug=workspace.slug)
        assert session_client.get(url).data["drafts"]["is_pinned"] is True

        session_client.patch(
            url,
            [
                {"key": "drafts", "is_pinned": False, "sort_order": 9},
                {"key": "app_rail:projects", "is_pinned": True, "sort_order": 0},
            ],
            format="json",
        )

        data = session_client.get(url).data
        assert data["drafts"] == {"is_pinned": False, "sort_order": 9}
        assert data["app_rail:projects"] == {"is_pinned": True, "sort_order": 0}

    def test_non_member_cannot_write(self, workspace):
        _, client = _member(None, 20)

        response = client.patch(
            PREFERENCES_URL.format(slug=workspace.slug),
            [{"key": "app_rail:projects", "is_pinned": False, "sort_order": 1}],
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not WorkspaceUserPreference.objects.filter(workspace=workspace, key="app_rail:projects").exists()
