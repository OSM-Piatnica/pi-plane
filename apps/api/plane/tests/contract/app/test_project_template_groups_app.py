# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Groups as members in project templates: saving, matching by path on upload, and applying to a new project."""

from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import (
    Project,
    ProjectGroup,
    ProjectMember,
    ProjectTemplate,
    User,
    UserGroup,
    UserGroupMember,
    Workspace,
    WorkspaceMember,
)

ADMIN, MEMBER, GUEST = 20, 15, 5


@pytest.fixture(autouse=True)
def _no_background_work(db):
    with mock.patch("plane.db.mixins.soft_delete_related_objects.delay"):
        yield


def templates_url(slug):
    return f"/api/workspaces/{slug}/project-templates/"


def apply_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/groups/from-project-template/"


@pytest.fixture
def parent(db, workspace):
    return UserGroup.objects.create(workspace=workspace, name="Plant")


@pytest.fixture
def child(db, workspace, parent):
    return UserGroup.objects.create(workspace=workspace, name="Night shift", parent=parent)


@pytest.mark.contract
@pytest.mark.django_db
class TestTemplateGroupsSaving:
    def create(self, client, workspace, groups, name="With groups"):
        return client.post(templates_url(workspace.slug), {"name": name, "payload": {"groups": groups}}, format="json")

    def test_groups_are_saved_with_their_current_path(self, session_client, workspace, child):
        response = self.create(session_client, workspace, [{"group": str(child.id), "role": GUEST}])

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["payload"]["groups"] == [
            {"group": str(child.id), "path": "Plant / Night shift", "role": GUEST}
        ]
        assert response.data["unmatched_groups"] == []

    def test_a_group_can_never_be_an_admin(self, session_client, workspace, parent):
        for role in (ADMIN, 0, "x", None):
            response = self.create(session_client, workspace, [{"group": str(parent.id), "role": role}])
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_a_malformed_entry_is_refused(self, session_client, workspace):
        assert self.create(session_client, workspace, [{"group": "nope", "role": MEMBER}]).status_code == 400
        assert self.create(session_client, workspace, [{"role": MEMBER}]).status_code == 400
        assert self.create(session_client, workspace, "x").status_code == 400

    def test_a_group_of_another_workspace_is_not_stored(self, session_client, workspace, create_user):
        other = Workspace.objects.create(name="Other", owner=create_user, slug="other-ws")
        foreign = UserGroup.objects.create(workspace=other, name="Foreign")

        response = self.create(session_client, workspace, [{"group": str(foreign.id), "role": MEMBER}])

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["payload"]["groups"] == []
        assert response.data["unmatched_groups"] == [{"group": str(foreign.id), "path": ""}]

    def test_an_uploaded_template_matches_groups_by_path_and_reports_the_rest(
        self, session_client, workspace, child, parent
    ):
        foreign_id = "11111111-1111-1111-1111-111111111111"
        response = self.create(
            session_client,
            workspace,
            [
                {"group": foreign_id, "path": "plant / night shift", "role": MEMBER},
                {"group": foreign_id.replace("1", "2"), "path": "Plant / Gone", "role": MEMBER},
                {"path": "Plant", "role": GUEST},
                {"group": str(parent.id), "role": MEMBER},
            ],
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["payload"]["groups"] == [
            {"group": str(child.id), "path": "Plant / Night shift", "role": MEMBER},
            {"group": str(parent.id), "path": "Plant", "role": GUEST},
        ]
        assert [u["path"] for u in response.data["unmatched_groups"]] == ["Plant / Gone"]

    def test_updating_a_template_validates_groups_too(self, session_client, workspace, parent):
        template = ProjectTemplate.objects.create(workspace=workspace, name="T", payload={})

        bad = session_client.patch(
            f"{templates_url(workspace.slug)}{template.id}/",
            {"payload": {"groups": [{"group": str(parent.id), "role": ADMIN}]}},
            format="json",
        )
        good = session_client.patch(
            f"{templates_url(workspace.slug)}{template.id}/",
            {"payload": {"groups": [{"group": str(parent.id), "role": MEMBER}]}},
            format="json",
        )

        assert bad.status_code == status.HTTP_400_BAD_REQUEST
        assert good.status_code == status.HTTP_200_OK
        assert good.data["payload"]["groups"][0]["role"] == MEMBER
        assert "unmatched_groups" in good.data

    def test_a_workspace_guest_cannot_save_templates(self, workspace, parent):
        from rest_framework.test import APIClient

        guest = User.objects.create(email="guest@example.test", username="guest")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=GUEST)
        client = APIClient()
        client.force_authenticate(user=guest)

        response = self.create(client, workspace, [{"group": str(parent.id), "role": MEMBER}])

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
@pytest.mark.django_db
class TestApplyTemplateGroups:
    @pytest.fixture
    def project(self, workspace, create_user):
        project = Project.objects.create(name="New", identifier="NEW", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=ADMIN)
        return project

    def test_groups_become_project_groups_and_bring_their_people(
        self, session_client, workspace, project, parent, child
    ):
        person = User.objects.create(email="p@example.test", username="p")
        WorkspaceMember.objects.create(workspace=workspace, member=person, role=MEMBER)
        UserGroupMember.objects.create(workspace=workspace, group=child, user=person)
        template = ProjectTemplate.objects.create(
            workspace=workspace,
            name="T",
            payload={"groups": [{"group": str(child.id), "path": "Plant / Night shift", "role": GUEST}]},
        )

        response = session_client.post(
            apply_url(workspace.slug, project.id), {"template_id": str(template.id)}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {"applied": 1, "skipped": []}
        assert ProjectGroup.objects.get(project=project, group=child).role == GUEST
        row = ProjectMember.objects.get(project=project, member=person)
        assert (row.role, row.via_group) == (GUEST, True)

    def test_a_group_deleted_since_is_skipped_and_reported(self, session_client, workspace, project, parent, child):
        template = ProjectTemplate.objects.create(
            workspace=workspace,
            name="T",
            payload={
                "groups": [
                    {"group": str(parent.id), "path": "Plant", "role": MEMBER},
                    {"group": str(child.id), "path": "Plant / Night shift", "role": MEMBER},
                ]
            },
        )
        child.delete()

        response = session_client.post(
            apply_url(workspace.slug, project.id), {"template_id": str(template.id)}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["applied"] == 1
        assert response.data["skipped"] == [{"group": str(child.id), "path": "Plant / Night shift"}]
        assert not ProjectGroup.objects.filter(project=project, group_id=child.id).exists()

    def test_applying_twice_does_not_duplicate(self, session_client, workspace, project, parent):
        template = ProjectTemplate.objects.create(
            workspace=workspace, name="T", payload={"groups": [{"group": str(parent.id), "role": MEMBER}]}
        )
        for _ in range(2):
            response = session_client.post(
                apply_url(workspace.slug, project.id), {"template_id": str(template.id)}, format="json"
            )
            assert response.status_code == status.HTTP_200_OK
        assert ProjectGroup.objects.filter(project=project).count() == 1

    def test_only_project_admins_apply_and_the_template_must_exist(self, workspace, project, parent, session_client):
        from rest_framework.test import APIClient

        member = User.objects.create(email="m@example.test", username="m")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=MEMBER)
        ProjectMember.objects.create(project=project, member=member, workspace=workspace, role=MEMBER)
        template = ProjectTemplate.objects.create(
            workspace=workspace, name="T", payload={"groups": [{"group": str(parent.id), "role": MEMBER}]}
        )
        client = APIClient()
        client.force_authenticate(user=member)

        denied = client.post(apply_url(workspace.slug, project.id), {"template_id": str(template.id)}, format="json")
        missing = session_client.post(
            apply_url(workspace.slug, project.id),
            {"template_id": "11111111-1111-1111-1111-111111111111"},
            format="json",
        )
        invalid = session_client.post(apply_url(workspace.slug, project.id), {}, format="json")

        assert denied.status_code == status.HTTP_403_FORBIDDEN
        assert missing.status_code == status.HTTP_404_NOT_FOUND
        assert invalid.status_code == status.HTTP_400_BAD_REQUEST
        assert not ProjectGroup.objects.filter(project=project).exists()
