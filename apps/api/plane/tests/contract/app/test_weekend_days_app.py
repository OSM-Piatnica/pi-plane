# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Weekend days: the workspace sets them, a new project copies them, a person can keep their own list."""

import pytest
from rest_framework import status

from plane.db.models import Profile, Project, ProjectMember, Workspace
from plane.utils.weekend_days import validate_weekend_days
from django.core.exceptions import ValidationError

FRIDAY_SATURDAY = [5, 6]
INVALID = [[7], [-1], [1, 1], [0, 1, 2, 3, 4, 5, 6], ["sat"], "6", [1.5], [True]]


def patch_workspace(client, workspace, **data):
    return client.patch(f"/api/workspaces/{workspace.slug}/", data, format="json")


def create_project(client, workspace, **extra):
    return client.post(
        f"/api/workspaces/{workspace.slug}/projects/",
        {"name": extra.pop("name", "Weekend"), "identifier": extra.pop("identifier", "WKD"), **extra},
        format="json",
    )


@pytest.mark.unit
class TestValidator:
    @pytest.mark.parametrize("value", [[0, 6], [6, 0], [5, 6], [3], [], None])
    def test_accepts(self, value):
        validate_weekend_days(value)

    @pytest.mark.parametrize("value", INVALID)
    def test_refuses(self, value):
        with pytest.raises(ValidationError):
            validate_weekend_days(value)


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkspaceSetting:
    def test_a_workspace_rests_on_saturday_and_sunday(self, workspace):
        assert workspace.weekend_days == [0, 6]

    def test_an_admin_can_change_it(self, session_client, workspace):
        response = patch_workspace(session_client, workspace, weekend_days=FRIDAY_SATURDAY)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.json()["weekend_days"] == FRIDAY_SATURDAY
        workspace.refresh_from_db()
        assert workspace.weekend_days == FRIDAY_SATURDAY

    def test_a_workspace_can_have_no_weekend(self, session_client, workspace):
        assert patch_workspace(session_client, workspace, weekend_days=[]).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("value", INVALID)
    def test_a_list_that_makes_no_sense_is_refused(self, session_client, workspace, value):
        assert patch_workspace(session_client, workspace, weekend_days=value).status_code == status.HTTP_400_BAD_REQUEST
        workspace.refresh_from_db()
        assert workspace.weekend_days == [0, 6]


@pytest.mark.contract
@pytest.mark.django_db
class TestNewProjects:
    def test_a_new_project_copies_the_workspace_days(self, session_client, workspace):
        Workspace.objects.filter(pk=workspace.pk).update(weekend_days=FRIDAY_SATURDAY)

        response = create_project(session_client, workspace)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.json()["weekend_days"] == FRIDAY_SATURDAY

    def test_days_chosen_for_the_project_are_kept(self, session_client, workspace):
        response = create_project(session_client, workspace, weekend_days=[0])

        assert Project.objects.get(pk=response.json()["id"]).weekend_days == [0]

    def test_an_empty_choice_is_not_replaced_by_the_workspace_days(self, session_client, workspace):
        response = create_project(session_client, workspace, weekend_days=[])

        assert Project.objects.get(pk=response.json()["id"]).weekend_days == []

    def test_an_existing_project_does_not_follow_later_workspace_changes(self, session_client, workspace):
        project_id = create_project(session_client, workspace).json()["id"]

        patch_workspace(session_client, workspace, weekend_days=FRIDAY_SATURDAY)

        assert Project.objects.get(pk=project_id).weekend_days == [0, 6]

    def test_a_project_admin_can_change_them_later(self, session_client, workspace, create_user):
        project_id = create_project(session_client, workspace).json()["id"]
        ProjectMember.objects.update_or_create(
            project_id=project_id, member=create_user, defaults={"role": 20, "is_active": True}
        )

        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project_id}/", {"weekend_days": [6]}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert Project.objects.get(pk=project_id).weekend_days == [6]

    @pytest.mark.parametrize("value", INVALID)
    def test_a_project_refuses_a_list_that_makes_no_sense(self, session_client, workspace, value):
        assert create_project(session_client, workspace, weekend_days=value).status_code == status.HTTP_400_BAD_REQUEST

    def test_the_public_api_copies_them_too(self, api_key_client, workspace):
        Workspace.objects.filter(pk=workspace.pk).update(weekend_days=FRIDAY_SATURDAY)

        response = api_key_client.post(
            f"/api/v1/workspaces/{workspace.slug}/projects/", {"name": "Public", "identifier": "PWD"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.json()["weekend_days"] == FRIDAY_SATURDAY


@pytest.mark.contract
@pytest.mark.django_db
class TestPersonalChoice:
    def test_a_new_profile_follows_the_workspace(self, create_user):
        profile, _ = Profile.objects.get_or_create(user=create_user)

        assert profile.weekend_days is None

    def test_a_person_can_pick_days_and_go_back_to_the_default(self, session_client, create_user):
        Profile.objects.get_or_create(user=create_user)
        url = "/api/users/me/profile/"

        picked = session_client.patch(url, {"weekend_days": FRIDAY_SATURDAY}, format="json")
        cleared = session_client.patch(url, {"weekend_days": None}, format="json")

        assert picked.status_code == status.HTTP_200_OK, picked.data
        assert picked.json()["weekend_days"] == FRIDAY_SATURDAY
        assert cleared.status_code == status.HTTP_200_OK, cleared.data
        assert cleared.json()["weekend_days"] is None

    @pytest.mark.parametrize("value", INVALID)
    def test_the_profile_refuses_a_list_that_makes_no_sense(self, session_client, create_user, value):
        Profile.objects.get_or_create(user=create_user)

        response = session_client.patch("/api/users/me/profile/", {"weekend_days": value}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
