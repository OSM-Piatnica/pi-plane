# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""``initiative_ids`` on the projects of the project list and of one project (roadmap F3, ``docs/initiatives.md``)."""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Initiative,
    InitiativeKind,
    InitiativeProject,
    Project,
    ProjectMember,
    User,
    WorkspaceFeature,
    WorkspaceMember,
)

SLUG = "test-workspace"
PROJECTS = f"/api/workspaces/{SLUG}/projects/details/"
MEMBER = 15


def _member(workspace):
    unique = uuid4().hex[:8]
    user = User.objects.create(email=f"member-{unique}@plane.so", username=f"member_{unique}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=MEMBER)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


def _project(workspace, identifier, members=()):
    project = Project.objects.create(name=f"{identifier} project", identifier=identifier, workspace=workspace)
    for user in members:
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=MEMBER)
    return project


def _by_id(response):
    assert response.status_code == 200, response.data
    # response.data holds the serializer's values, where an id is a UUID, not text
    return {str(row["id"]): row for row in response.data}


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectListInitiatives:
    def test_each_project_lists_its_initiatives(self, session_client, workspace, create_user):
        WorkspaceFeature.objects.create(workspace=workspace, key="initiatives", is_enabled=True)
        both = _project(workspace, "BOTH", [create_user])
        none = _project(workspace, "NONE", [create_user])
        goal = Initiative.objects.create(workspace=workspace, name="Goal", kind=InitiativeKind.GOAL)
        first = Initiative.objects.create(workspace=workspace, name="First", parent=goal, sort_order=1)
        second = Initiative.objects.create(workspace=workspace, name="Second", sort_order=2)
        InitiativeProject.objects.create(initiative=second, project=both)
        InitiativeProject.objects.create(initiative=first, project=both)

        rows = _by_id(session_client.get(PROJECTS))

        assert rows[str(both.id)]["initiative_ids"] == [str(first.id), str(second.id)]
        assert rows[str(none.id)]["initiative_ids"] == []

    def test_empty_while_the_feature_is_off(self, session_client, workspace, create_user):
        project = _project(workspace, "OFF", [create_user])
        InitiativeProject.objects.create(
            initiative=Initiative.objects.create(workspace=workspace, name="Hidden"), project=project
        )

        rows = _by_id(session_client.get(PROJECTS))

        assert rows[str(project.id)]["initiative_ids"] == []

    def test_a_project_the_member_may_not_see_into_does_not_tell_its_initiatives(self, workspace):
        WorkspaceFeature.objects.create(workspace=workspace, key="initiatives", is_enabled=True)
        member, client = _member(workspace)
        mine = _project(workspace, "MINE", [member])
        # A public project the member is not in: listed, but its numbers are not theirs to see
        public = _project(workspace, "PUB")
        initiative = Initiative.objects.create(workspace=workspace, name="Shared")
        InitiativeProject.objects.create(initiative=initiative, project=mine)
        InitiativeProject.objects.create(initiative=initiative, project=public)

        rows = _by_id(client.get(PROJECTS))

        assert rows[str(mine.id)]["initiative_ids"] == [str(initiative.id)]
        assert rows[str(public.id)]["initiative_ids"] == []

    def test_one_project_carries_its_initiatives_too(self, session_client, workspace, create_user):
        WorkspaceFeature.objects.create(workspace=workspace, key="initiatives", is_enabled=True)
        project = _project(workspace, "ONE", [create_user])
        initiative = Initiative.objects.create(workspace=workspace, name="One")
        InitiativeProject.objects.create(initiative=initiative, project=project)

        response = session_client.get(f"/api/workspaces/{SLUG}/projects/{project.id}/")

        assert response.status_code == 200, response.data
        assert response.data["initiative_ids"] == [str(initiative.id)]
