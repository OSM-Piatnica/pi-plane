# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the default workspace short links of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""The instance setting that gives one workspace compact `/i/PROJ-123` work item links."""

from uuid import uuid4

import pytest
from django.core.cache import cache
from django.utils import timezone

from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration

KEY = "INSTANCE_DEFAULT_WORKSPACE_ID"
CONFIGURATIONS = "/api/instances/configurations/"
INSTANCE = "/api/instances/"


@pytest.fixture(autouse=True)
def clear_cache():
    """Both endpoints cache their answer for hours, and tests share the cache."""
    cache.clear()
    yield
    cache.clear()


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
    return InstanceConfiguration.objects.create(key=KEY, value="", category="WORKSPACE_MANAGEMENT")


@pytest.mark.contract
@pytest.mark.django_db
class TestDefaultWorkspaceSetting:
    def test_an_instance_admin_can_choose_a_workspace(self, session_client, instance_admin, setting, workspace):
        response = session_client.patch(CONFIGURATIONS, {KEY: str(workspace.id)}, format="json")

        assert response.status_code == 200, response.data
        setting.refresh_from_db()
        assert setting.value == str(workspace.id)

    def test_an_instance_admin_can_clear_the_choice(self, session_client, instance_admin, setting, workspace):
        setting.value = str(workspace.id)
        setting.save()

        response = session_client.patch(CONFIGURATIONS, {KEY: ""}, format="json")

        assert response.status_code == 200, response.data
        setting.refresh_from_db()
        assert setting.value == ""

    def test_an_unknown_workspace_is_rejected(self, session_client, instance_admin, setting):
        response = session_client.patch(CONFIGURATIONS, {KEY: str(uuid4())}, format="json")

        assert response.status_code == 400
        assert "does not exist" in response.data["error"]
        setting.refresh_from_db()
        assert setting.value == ""

    def test_a_malformed_value_is_rejected(self, session_client, instance_admin, setting):
        response = session_client.patch(CONFIGURATIONS, {KEY: "not-a-workspace"}, format="json")

        assert response.status_code == 400
        assert "not valid" in response.data["error"]
        setting.refresh_from_db()
        assert setting.value == ""

    def test_only_an_instance_admin_can_change_it(self, session_client, instance, setting, workspace):
        response = session_client.patch(CONFIGURATIONS, {KEY: str(workspace.id)}, format="json")

        assert response.status_code == 403
        setting.refresh_from_db()
        assert setting.value == ""


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicInstanceConfig:
    def test_reports_the_chosen_workspace_to_anyone(self, api_client, instance, setting, workspace):
        setting.value = str(workspace.id)
        setting.save()

        response = api_client.get(INSTANCE)

        assert response.status_code == 200
        assert response.data["config"]["default_workspace_id"] == str(workspace.id)

    def test_reports_nothing_when_unset(self, api_client, instance, setting):
        response = api_client.get(INSTANCE)

        assert response.data["config"]["default_workspace_id"] == ""

    def test_a_stale_workspace_is_treated_as_disabled(self, api_client, instance, setting):
        """The endpoint is public, so it must not advertise a route that cannot be resolved."""
        setting.value = str(uuid4())
        setting.save()

        response = api_client.get(INSTANCE)

        assert response.data["config"]["default_workspace_id"] == ""

    def test_a_malformed_stored_value_is_treated_as_disabled(self, api_client, instance, setting):
        setting.value = "garbage"
        setting.save()

        response = api_client.get(INSTANCE)

        assert response.status_code == 200
        assert response.data["config"]["default_workspace_id"] == ""
