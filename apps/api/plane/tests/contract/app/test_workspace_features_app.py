# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the workspace feature switches.

Only ``raci`` is available as shipped. The tests of the mechanism make ``approvals`` the one available feature for
their own duration, so that they do not depend on which features are built.
"""

from unittest import mock
from uuid import uuid4

import pytest
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import User, Workspace, WorkspaceFeature, WorkspaceMember
from plane.utils import workspace_features
from plane.utils.workspace_features import WORKSPACE_FEATURES, enabled_workspace_feature_keys, set_workspace_feature

URL = "/api/workspaces/{slug}/features/"
WORKSPACES_URL = "/api/users/me/workspaces/"


def _client(workspace, role):
    unique = uuid4().hex[:8]
    user = User.objects.create(email=f"feature-{role}-{unique}@plane.so", username=f"feature_{role}_{unique}")
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=role, is_active=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def approvals_available(monkeypatch):
    monkeypatch.setitem(workspace_features.WORKSPACE_FEATURES, "approvals", True)
    monkeypatch.setitem(workspace_features.WORKSPACE_FEATURES, "raci", False)


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkspaceFeaturesAsShipped:
    """Only RACI is built; the other switches cannot be used yet."""

    def test_known_keys_and_only_raci_available(self):
        assert set(WORKSPACE_FEATURES) == {"lite", "approvals", "initiatives", "wiki", "raci"}
        assert [key for key, available in WORKSPACE_FEATURES.items() if available] == ["raci"]

    def test_read_lists_the_available_features(self, session_client, workspace):
        response = session_client.get(URL.format(slug=workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"raci": False}

    @pytest.mark.parametrize("key", [key for key, available in WORKSPACE_FEATURES.items() if not available])
    def test_unavailable_feature_cannot_be_switched_on(self, session_client, workspace, key):
        response = session_client.patch(URL.format(slug=workspace.slug), {key: True}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert key in response.data
        assert not WorkspaceFeature.objects.filter(workspace=workspace).exists()

    def test_row_of_an_unavailable_feature_is_not_reported(self, session_client, workspace):
        WorkspaceFeature.objects.create(workspace=workspace, key="approvals", is_enabled=True)

        assert enabled_workspace_feature_keys(workspace) == []
        response = session_client.get(WORKSPACES_URL)
        assert response.status_code == status.HTTP_200_OK
        assert [row["enabled_features"] for row in response.data] == [[]]


@pytest.mark.contract
@pytest.mark.django_db
@pytest.mark.usefixtures("approvals_available")
class TestWorkspaceFeatureSwitches:
    def test_default_is_off(self, session_client, workspace):
        response = session_client.get(URL.format(slug=workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"approvals": False}
        assert not WorkspaceFeature.objects.filter(workspace=workspace).exists()

    @pytest.mark.parametrize("role", [20, 15, 5])
    def test_every_member_reads(self, workspace, role):
        WorkspaceFeature.objects.create(workspace=workspace, key="approvals", is_enabled=True)

        response = _client(workspace, role).get(URL.format(slug=workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"approvals": True}

    def test_non_member_cannot_read(self, workspace):
        response = _client(None, 20).get(URL.format(slug=workspace.slug))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_anonymous_cannot_read(self, api_client, workspace):
        response = api_client.get(URL.format(slug=workspace.slug))

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_admin_switches_on_and_off(self, session_client, workspace):
        url = URL.format(slug=workspace.slug)

        response = session_client.patch(url, {"approvals": True}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"approvals": True}
        assert session_client.get(url).data == {"approvals": True}

        response = session_client.patch(url, {"approvals": False}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"approvals": False}
        # one row per workspace and key, updated in place
        assert WorkspaceFeature.objects.filter(workspace=workspace, key="approvals").count() == 1

    @pytest.mark.parametrize("role", [15, 5])
    def test_member_and_guest_cannot_switch(self, workspace, role):
        response = _client(workspace, role).patch(URL.format(slug=workspace.slug), {"approvals": True}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not WorkspaceFeature.objects.filter(workspace=workspace).exists()

    def test_admin_of_another_workspace_cannot_switch(self, workspace, create_user):
        other = Workspace.objects.create(name="Other", owner=create_user, slug="other-workspace")

        response = _client(other, 20).patch(URL.format(slug=workspace.slug), {"approvals": True}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not WorkspaceFeature.objects.filter(workspace=workspace).exists()

    @pytest.mark.parametrize(
        "payload",
        [
            {"unknown_feature": True},
            {"wiki": True},  # known, not available
            {"approvals": "yes"},
            {"approvals": 1},
            {"approvals": None},
            {},
            ["approvals"],
        ],
    )
    def test_invalid_payload_is_rejected(self, session_client, workspace, payload):
        response = session_client.patch(URL.format(slug=workspace.slug), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not WorkspaceFeature.objects.filter(workspace=workspace).exists()

    def test_one_wrong_entry_saves_nothing(self, session_client, workspace):
        response = session_client.patch(
            URL.format(slug=workspace.slug), {"approvals": True, "wiki": True}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert set(response.data) == {"wiki"}
        assert not WorkspaceFeature.objects.filter(workspace=workspace).exists()

    def test_switch_is_per_workspace(self, session_client, workspace, create_user):
        other = Workspace.objects.create(name="Other", owner=create_user, slug="other-workspace")
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)

        session_client.patch(URL.format(slug=workspace.slug), {"approvals": True}, format="json")

        assert session_client.get(URL.format(slug=other.slug)).data == {"approvals": False}

    def test_workspace_payload_lists_enabled_features(self, session_client, workspace):
        assert [row["enabled_features"] for row in session_client.get(WORKSPACES_URL).data] == [[]]

        session_client.patch(URL.format(slug=workspace.slug), {"approvals": True}, format="json")

        assert [row["enabled_features"] for row in session_client.get(WORKSPACES_URL).data] == [["approvals"]]

    def test_guest_sees_enabled_features_in_the_workspace_payload(self, workspace):
        WorkspaceFeature.objects.create(workspace=workspace, key="approvals", is_enabled=True)

        response = _client(workspace, 5).get(WORKSPACES_URL)

        assert response.status_code == status.HTTP_200_OK
        assert [row["enabled_features"] for row in response.data] == [["approvals"]]

    def test_enabled_features_cannot_be_written_through_the_workspace(self, session_client, workspace):
        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/", {"enabled_features": ["approvals"]}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert not WorkspaceFeature.objects.filter(workspace=workspace).exists()

    def test_lost_create_race_updates_the_row_instead_of_failing(self, workspace):
        # the other admin's request created the row between our lookup and our insert
        WorkspaceFeature.objects.create(workspace=workspace, key="approvals", is_enabled=False)

        with mock.patch.object(WorkspaceFeature.objects, "update_or_create", side_effect=IntegrityError):
            set_workspace_feature(workspace, "approvals", True)

        rows = WorkspaceFeature.objects.filter(workspace=workspace, key="approvals")
        assert rows.count() == 1
        assert rows.get().is_enabled is True

    def test_workspace_lists_read_the_switches_in_one_query(self, session_client, workspace, create_user):
        url = WORKSPACES_URL
        WorkspaceFeature.objects.create(workspace=workspace, key="approvals", is_enabled=True)
        with CaptureQueriesContext(connection) as one_workspace:
            response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        for index in range(2):
            other = Workspace.objects.create(name=f"Other {index}", owner=create_user, slug=f"other-workspace-{index}")
            WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)
            WorkspaceFeature.objects.create(workspace=other, key="approvals", is_enabled=True)
        with CaptureQueriesContext(connection) as three_workspaces:
            response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert [row["enabled_features"] for row in response.data] == [["approvals"]] * 3
        assert len(three_workspaces.captured_queries) == len(one_workspace.captured_queries)
