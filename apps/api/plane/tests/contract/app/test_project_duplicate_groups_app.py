# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Duplicating a project with its groups as members (``include.groups``)."""

import pytest
from django.core.cache import cache
from rest_framework import status

from plane.db.models import (
    Project,
    ProjectGroup,
    ProjectMember,
    State,
    User,
    UserGroup,
    UserGroupMember,
    WorkspaceMember,
)
from plane.utils.project_groups import reconcile_project

ADMIN = 20
MEMBER = 15
GUEST = 5


def duplicate_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/duplicate/"


def make_user(workspace, name, workspace_role=MEMBER):
    user = User.objects.create(email=f"{name}@example.test", username=name)
    user.set_password("test-password")
    user.save()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=workspace_role)
    return user


@pytest.fixture(autouse=True)
def clear_throttles():
    cache.clear()


@pytest.fixture
def source_project(db, workspace, create_user):
    project = Project.objects.create(
        name="Source Project", identifier="SRC", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=ADMIN)
    State.objects.create(
        name="Backlog", color="#000", group="backlog", project=project, workspace=workspace, sequence=1
    )
    return project


@pytest.fixture
def team(db, workspace):
    """A group the source is linked to."""
    return UserGroup.objects.create(workspace=workspace, name="Team")


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectDuplicateGroups:
    @pytest.fixture
    def setup(self, workspace, source_project, team):
        direct = make_user(workspace, "direct")
        through_group = make_user(workspace, "viagroup")
        raised = make_user(workspace, "raised")
        for user in (through_group, raised):
            UserGroupMember.objects.create(workspace=workspace, group=team, user=user)
        ProjectMember.objects.create(project=source_project, member=direct, workspace=workspace, role=MEMBER)
        # raised is a Guest of their own accord, raised to Member by the group
        ProjectMember.objects.create(project=source_project, member=raised, workspace=workspace, role=GUEST)
        ProjectGroup.objects.create(project=source_project, workspace=workspace, group=team, role=MEMBER)
        reconcile_project(source_project.id)
        return {"direct": direct, "via": through_group, "raised": raised}

    def post(self, client, workspace, source_project, include):
        return client.post(duplicate_url(workspace.slug, source_project.id), {"include": include}, format="json")

    def test_groups_are_not_copied_unless_asked_for(self, session_client, workspace, source_project, setup):
        response = self.post(session_client, workspace, source_project, {"members": True})

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert not ProjectGroup.objects.filter(project_id=response.data["id"]).exists()

    def test_groups_alone_copy_the_links_and_bring_their_people(
        self, session_client, workspace, source_project, team, setup
    ):
        response = self.post(session_client, workspace, source_project, {"groups": True})

        assert response.status_code == status.HTTP_201_CREATED, response.data
        copy_id = response.data["id"]
        link = ProjectGroup.objects.get(project_id=copy_id)
        assert (link.group_id, link.role) == (team.id, MEMBER)
        via = ProjectMember.objects.get(project_id=copy_id, member=setup["via"])
        assert via.via_group is True and via.role == MEMBER
        # the direct member is not carried by name; the person only in the group is
        assert not ProjectMember.objects.filter(project_id=copy_id, member=setup["direct"]).exists()
        assert response.data["copy_summary"]["counts"]["groups"] == 1

    def test_members_and_groups_copy_direct_members_with_their_own_role(
        self, session_client, workspace, source_project, setup, create_user
    ):
        response = self.post(session_client, workspace, source_project, {"members": True, "groups": True})

        copy_id = response.data["id"]
        raised = ProjectMember.objects.get(project_id=copy_id, member=setup["raised"])
        # Guest on their own, raised to Member by the group: the copy reproduces both
        assert (raised.role, raised.direct_role, raised.group_role, raised.via_group) == (MEMBER, GUEST, MEMBER, False)
        direct = ProjectMember.objects.get(project_id=copy_id, member=setup["direct"])
        assert (direct.role, direct.direct_role, direct.group_role, direct.via_group) == (MEMBER, None, None, False)
        via = ProjectMember.objects.get(project_id=copy_id, member=setup["via"])
        assert via.via_group is True
        creator = ProjectMember.objects.get(project_id=copy_id, member=create_user)
        assert creator.role == ADMIN

    def test_members_without_groups_copy_everyone_as_plain_members(
        self, session_client, workspace, source_project, setup
    ):
        response = self.post(session_client, workspace, source_project, {"members": True})

        copy_id = response.data["id"]
        assert not ProjectGroup.objects.filter(project_id=copy_id).exists()
        for key in ("direct", "via", "raised"):
            row = ProjectMember.objects.get(project_id=copy_id, member=setup[key])
            assert (row.via_group, row.group_role, row.direct_role) == (False, None, None)
        assert ProjectMember.objects.get(project_id=copy_id, member=setup["raised"]).role == MEMBER

    def test_people_added_through_groups_count_against_the_member_cap(
        self, session_client, workspace, source_project, setup, monkeypatch
    ):
        monkeypatch.setattr("plane.utils.project_duplicate.MAX_MEMBERS", 1)

        response = self.post(session_client, workspace, source_project, {"groups": True})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "PROJECT_TOO_LARGE_TO_COPY_SYNCHRONOUSLY"
        assert not Project.objects.filter(name__startswith="Source Project (").exists()

    def test_a_deleted_group_is_not_copied(self, session_client, workspace, source_project, team, setup):
        team.delete()

        response = self.post(session_client, workspace, source_project, {"groups": True})

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert not ProjectGroup.objects.filter(project_id=response.data["id"]).exists()
