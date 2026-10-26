# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""First day of the week: the workspace sets it, a new project copies it, a person's own choice wins in the UI."""

import importlib

import pytest
from django.apps import apps
from rest_framework import status

from plane.db.models import Profile, Project, ProjectMember

MONDAY = 1
SATURDAY = 6


def create_project(client, workspace, **extra):
    return client.post(
        f"/api/workspaces/{workspace.slug}/projects/",
        {"name": extra.pop("name", "Weeks"), "identifier": extra.pop("identifier", "WKS"), **extra},
        format="json",
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkspaceSetting:
    def test_a_workspace_starts_its_week_on_sunday(self, workspace):
        assert workspace.start_of_the_week == 0

    def test_an_admin_can_change_it(self, session_client, workspace):
        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/", {"start_of_the_week": MONDAY}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        workspace.refresh_from_db()
        assert workspace.start_of_the_week == MONDAY
        assert response.json()["start_of_the_week"] == MONDAY

    def test_a_day_that_does_not_exist_is_refused(self, session_client, workspace):
        response = session_client.patch(f"/api/workspaces/{workspace.slug}/", {"start_of_the_week": 7}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
@pytest.mark.django_db
class TestNewProjects:
    def test_a_new_project_copies_the_workspace_setting(self, session_client, workspace):
        type(workspace).objects.filter(pk=workspace.pk).update(start_of_the_week=MONDAY)

        response = create_project(session_client, workspace)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.json()["start_of_the_week"] == MONDAY
        assert Project.objects.get(pk=response.json()["id"]).start_of_the_week == MONDAY

    def test_a_day_chosen_for_the_project_is_kept(self, session_client, workspace):
        type(workspace).objects.filter(pk=workspace.pk).update(start_of_the_week=MONDAY)

        response = create_project(session_client, workspace, start_of_the_week=SATURDAY)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Project.objects.get(pk=response.json()["id"]).start_of_the_week == SATURDAY

    def test_sunday_chosen_on_purpose_is_not_replaced_by_the_workspace_day(self, session_client, workspace):
        type(workspace).objects.filter(pk=workspace.pk).update(start_of_the_week=MONDAY)

        response = create_project(session_client, workspace, start_of_the_week=0)

        assert Project.objects.get(pk=response.json()["id"]).start_of_the_week == 0

    def test_an_existing_project_does_not_follow_later_workspace_changes(self, session_client, workspace):
        project_id = create_project(session_client, workspace).json()["id"]

        session_client.patch(f"/api/workspaces/{workspace.slug}/", {"start_of_the_week": MONDAY}, format="json")

        assert Project.objects.get(pk=project_id).start_of_the_week == 0

    def test_the_timezone_is_still_copied_too(self, session_client, workspace):
        type(workspace).objects.filter(pk=workspace.pk).update(timezone="Europe/Warsaw", start_of_the_week=MONDAY)

        project = Project.objects.get(pk=create_project(session_client, workspace).json()["id"])

        assert (project.timezone, project.start_of_the_week) == ("Europe/Warsaw", MONDAY)

    def test_a_project_admin_can_change_it_later(self, session_client, workspace, create_user):
        project_id = create_project(session_client, workspace).json()["id"]
        ProjectMember.objects.update_or_create(
            project_id=project_id, member=create_user, defaults={"role": 20, "is_active": True}
        )

        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project_id}/", {"start_of_the_week": SATURDAY}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert Project.objects.get(pk=project_id).start_of_the_week == SATURDAY

    def test_the_public_api_copies_it_too(self, api_key_client, workspace):
        type(workspace).objects.filter(pk=workspace.pk).update(start_of_the_week=MONDAY)

        response = api_key_client.post(
            f"/api/v1/workspaces/{workspace.slug}/projects/", {"name": "Public", "identifier": "PUB"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.json()["start_of_the_week"] == MONDAY


@pytest.mark.contract
@pytest.mark.django_db
class TestPersonalChoice:
    def test_a_new_profile_has_no_choice_of_its_own(self, create_user):
        profile, _ = Profile.objects.get_or_create(user=create_user)

        assert profile.start_of_the_week is None

    def test_a_person_can_pick_a_day_and_go_back_to_the_project_default(self, session_client, create_user):
        Profile.objects.get_or_create(user=create_user)

        picked = session_client.patch("/api/users/me/profile/", {"start_of_the_week": MONDAY}, format="json")
        cleared = session_client.patch("/api/users/me/profile/", {"start_of_the_week": None}, format="json")

        assert picked.status_code == status.HTTP_200_OK, picked.data
        assert picked.json()["start_of_the_week"] == MONDAY
        assert cleared.status_code == status.HTTP_200_OK, cleared.data
        assert cleared.json()["start_of_the_week"] is None


@pytest.mark.contract
@pytest.mark.django_db
class TestMigration:
    def test_sunday_profiles_follow_the_default_and_other_days_stay(self, create_user, db):
        from plane.db.models import User

        migration = importlib.import_module("plane.db.migrations.0147_start_of_the_week_workspace_project")
        other = User.objects.create(email="other@plane.so", username="other")
        first, _ = Profile.objects.get_or_create(user=create_user)
        second, _ = Profile.objects.get_or_create(user=other)
        Profile.objects.filter(pk=first.pk).update(start_of_the_week=0)
        Profile.objects.filter(pk=second.pk).update(start_of_the_week=MONDAY)

        migration.follow_the_default(apps, None)

        first.refresh_from_db()
        second.refresh_from_db()
        assert first.start_of_the_week is None
        assert second.start_of_the_week == MONDAY

        migration.back_to_sunday(apps, None)
        first.refresh_from_db()
        assert first.start_of_the_week == 0
