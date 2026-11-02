# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Instance themes: everybody lists them, instance admins manage them, deployment ones stay read-only."""

import json
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone

from plane.license.models import Instance, InstanceAdmin, InstanceTheme

THEMES = "/api/instances/themes/"
THEME = {"name": "Piątnica Dark", "primary": "#4F8F7D", "background": "#404040", "dark_palette": True}


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


@pytest.mark.contract
@pytest.mark.django_db
class TestInstanceThemes:
    def test_any_signed_in_user_lists_the_themes(self, session_client, instance):
        InstanceTheme.objects.create(**{**THEME, "source": "deployment"})
        response = session_client.get(THEMES)
        assert response.status_code == 200
        assert [t["name"] for t in response.data] == ["Piątnica Dark"]
        assert response.data[0]["is_read_only"] is True

    def test_anonymous_cannot_list(self, api_client, instance):
        assert api_client.get(THEMES).status_code in (401, 403)

    def test_a_member_cannot_add(self, session_client, instance):
        assert session_client.post(THEMES, THEME, format="json").status_code == 403

    def test_admin_adds_edits_and_deletes(self, session_client, instance_admin):
        created = session_client.post(THEMES, {**THEME, "overrides": {"bg-canvas": "#2E2E2E"}}, format="json")
        assert created.status_code == 201
        assert created.data["source"] == "admin"
        assert created.data["primary"] == "#4f8f7d"
        assert created.data["overrides"] == {"bg-canvas": "#2e2e2e"}

        url = f"{THEMES}{created.data['id']}/"
        assert session_client.patch(url, {"name": "Renamed"}, format="json").data["name"] == "Renamed"
        assert session_client.delete(url).status_code == 204
        assert not InstanceTheme.objects.exists()
        # the name of a deleted theme can be used again
        assert session_client.post(THEMES, {**THEME, "name": "Renamed"}, format="json").status_code == 201

    def test_rejects_bad_colours_and_duplicate_names(self, session_client, instance_admin):
        assert session_client.post(THEMES, {**THEME, "primary": "green"}, format="json").status_code == 400
        assert (
            session_client.post(THEMES, {**THEME, "overrides": {"bg-canvas": "nope"}}, format="json").status_code == 400
        )
        assert session_client.post(THEMES, THEME, format="json").status_code == 201
        assert session_client.post(THEMES, {**THEME, "name": "piątnica dark"}, format="json").status_code == 409

    def test_deployment_themes_are_read_only(self, session_client, instance_admin):
        theme = InstanceTheme.objects.create(**{**THEME, "source": "deployment"})
        url = f"{THEMES}{theme.id}/"
        assert session_client.patch(url, {"name": "X"}, format="json").status_code == 403
        assert session_client.delete(url).status_code == 403
        assert InstanceTheme.objects.filter(pk=theme.pk).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestLoadInstanceThemes:
    def test_loads_replaces_and_removes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INSTANCE_THEMES_DIR", str(tmp_path))
        (tmp_path / "dark.json").write_text(
            json.dumps(
                {"themeName": "Piątnica Dark", "primary": "#4F8F7D", "background": "#404040", "darkPalette": True}
            )
        )
        (tmp_path / "broken.json").write_text(json.dumps({"themeName": "Broken", "primary": "x"}))
        # a theme added in the GUI under the same name gives way to the deployment
        InstanceTheme.objects.create(**{**THEME, "primary": "#000000", "source": "admin"})

        call_command("load_instance_themes")
        theme = InstanceTheme.objects.get()
        assert (theme.primary, theme.source, theme.dark_palette) == ("#4f8f7d", "deployment", True)

        (tmp_path / "dark.json").unlink()
        call_command("load_instance_themes")
        assert not InstanceTheme.objects.exists()
