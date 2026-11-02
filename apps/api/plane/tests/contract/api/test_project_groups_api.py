# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests: user groups as members of a project through the public API (API key authentication).

GET/POST   /api/v1/workspaces/<slug>/projects/<project_id>/groups/
PATCH/DELETE /api/v1/workspaces/<slug>/projects/<project_id>/groups/<id>/
"""

from unittest import mock
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Project,
    ProjectGroup,
    ProjectMember,
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


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Groups", identifier="PGA", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    return project


def _person(workspace, project=None, ws_role=MEMBER, project_role=None):
    uid = uuid4().hex[:8]
    user = User.objects.create(email=f"u-{uid}@plane.so", username=f"u_{uid}", first_name=f"user{uid}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=ws_role)
    if project_role is not None:
        ProjectMember.objects.create(
            project=project, member=user, workspace=workspace, role=project_role, is_active=True
        )
    return user


def _client(user):
    token = APIToken.objects.create(user=user, label="t")
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token.token)
    return client


def _group(workspace, name, parent=None):
    return UserGroup.objects.create(workspace=workspace, name=name, parent=parent)


def _join(group, user):
    return UserGroupMember.objects.create(workspace=group.workspace, group=group, user=user)


def _url(workspace, project, suffix=""):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/groups/{suffix}"


def _members_url(workspace, project, suffix=""):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/members/{suffix}"


def _link(client, workspace, project, group, role=MEMBER):
    return client.post(_url(workspace, project), {"group": str(group.id), "role": role}, format="json")


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectGroupsApi:
    def test_adding_a_group_makes_its_people_members_with_its_role(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace)
        _join(sales, ada)

        response = _link(api_key_client, workspace, project, sales, GUEST)

        assert response.status_code == 201, response.data
        assert response.data["group_name"] == "Sales"
        assert response.data["role"] == GUEST
        assert response.data["member_count"] == 1
        row = ProjectMember.objects.get(project=project, member=ada)
        assert (row.is_active, row.via_group, row.role, row.group_role, row.direct_role) == (
            True,
            True,
            GUEST,
            GUEST,
            None,
        )

    def test_subgroup_people_are_members_too_and_the_list_counts_them(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        ada = _person(workspace)
        _join(poland, ada)

        _link(api_key_client, workspace, project, sales)

        assert ProjectMember.objects.get(project=project, member=ada).role == MEMBER
        listed = api_key_client.get(_url(workspace, project))
        assert listed.status_code == 200
        assert [(g["group"], g["member_count"]) for g in listed.json()] == [(str(sales.id), 1)]

    def test_a_group_cannot_be_admin_and_the_role_is_required(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")

        assert _link(api_key_client, workspace, project, sales, ADMIN).status_code == 400
        assert _link(api_key_client, workspace, project, sales, 7).status_code == 400
        no_role = api_key_client.post(_url(workspace, project), {"group": str(sales.id)}, format="json")
        assert no_role.status_code == 400
        assert not ProjectGroup.objects.filter(project=project).exists()

    def test_a_foreign_group_is_refused_with_the_app_message_and_a_duplicate_conflicts(
        self, api_key_client, workspace, project, create_user
    ):
        other = Workspace.objects.create(name="Other", slug="other", owner=create_user)
        foreign = _group(other, "Foreign")
        sales = _group(workspace, "Sales")

        refused = _link(api_key_client, workspace, project, foreign)
        assert refused.status_code == 400
        assert refused.data == {"error": "The group does not exist in this workspace."}

        assert _link(api_key_client, workspace, project, sales).status_code == 201
        duplicate = _link(api_key_client, workspace, project, sales)
        assert duplicate.status_code == 409
        assert duplicate.data == {"error": "This group is already a member of the project."}

    def test_an_unknown_group_is_a_validation_error(self, api_key_client, workspace, project):
        response = api_key_client.post(_url(workspace, project), {"group": str(uuid4()), "role": MEMBER}, format="json")

        assert response.status_code == 400
        assert not ProjectGroup.objects.filter(project=project).exists()

    def test_patch_changes_only_the_role_and_reconciles(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        other = _group(workspace, "Other")
        ada = _person(workspace)
        _join(sales, ada)
        link_id = _link(api_key_client, workspace, project, sales, MEMBER).data["id"]

        response = api_key_client.patch(
            _url(workspace, project, f"{link_id}/"), {"role": GUEST, "group": str(other.id)}, format="json"
        )

        assert response.status_code == 200, response.data
        assert response.data["role"] == GUEST
        assert response.json()["group"] == str(sales.id)
        assert ProjectMember.objects.get(project=project, member=ada).role == GUEST

    def test_patch_refuses_admin_and_a_missing_link_is_404(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        link_id = _link(api_key_client, workspace, project, sales).data["id"]

        assert (
            api_key_client.patch(_url(workspace, project, f"{link_id}/"), {"role": ADMIN}, format="json").status_code
            == 400
        )
        missing = api_key_client.patch(_url(workspace, project, f"{uuid4()}/"), {"role": GUEST}, format="json")
        assert missing.status_code == 404
        assert missing.data == {"error": "Group not found in the project."}
        assert api_key_client.delete(_url(workspace, project, f"{uuid4()}/")).status_code == 404

    def test_delete_removes_the_link_and_the_people_who_were_only_there_through_it(
        self, api_key_client, workspace, project
    ):
        sales = _group(workspace, "Sales")
        ada = _person(workspace)
        _join(sales, ada)
        link_id = _link(api_key_client, workspace, project, sales).data["id"]

        response = api_key_client.delete(_url(workspace, project, f"{link_id}/"))

        assert response.status_code == 204
        assert not ProjectGroup.objects.filter(project=project).exists()
        assert not ProjectMember.objects.filter(project=project, member=ada, is_active=True).exists()

    def test_a_link_of_another_project_is_not_reachable(self, api_key_client, workspace, project, create_user):
        sales = _group(workspace, "Sales")
        other_project = Project.objects.create(name="Other", identifier="OTP", workspace=workspace)
        ProjectMember.objects.create(project=other_project, member=create_user, role=ADMIN, is_active=True)
        link_id = _link(api_key_client, workspace, other_project, sales).data["id"]

        assert api_key_client.delete(_url(workspace, project, f"{link_id}/")).status_code == 404
        assert ProjectGroup.objects.filter(pk=link_id).exists()

    def test_assignable_lists_the_project_groups_and_the_groups_below_them(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        _group(workspace, "Unrelated")
        _link(api_key_client, workspace, project, sales)

        response = api_key_client.get(_url(workspace, project) + "?assignable=1")

        assert response.status_code == 200
        assert [(g["id"], g["parent_id"]) for g in response.json()] == [
            (str(poland.id), str(sales.id)),
            (str(sales.id), None),
        ]
        assert set(response.json()[0]) == {"id", "name", "source", "parent_id"}


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectGroupsPermissionMatrix:
    def test_project_members_and_guests_read_but_cannot_change(self, workspace, project):
        sales = _group(workspace, "Sales")
        link = ProjectGroup.objects.create(project=project, workspace=workspace, group=sales, role=MEMBER)
        for ws_role, project_role in ((MEMBER, MEMBER), (GUEST, GUEST), (MEMBER, GUEST)):
            client = _client(_person(workspace, project, ws_role, project_role))

            assert client.get(_url(workspace, project)).status_code == 200
            assert client.get(_url(workspace, project) + "?assignable=1").status_code == 200
            assert _link(client, workspace, project, _group(workspace, uuid4().hex[:6])).status_code == 403
            assert (
                client.patch(_url(workspace, project, f"{link.id}/"), {"role": GUEST}, format="json").status_code == 403
            )
            assert client.delete(_url(workspace, project, f"{link.id}/")).status_code == 403

        link.refresh_from_db()
        assert link.role == MEMBER

    def test_a_project_admin_who_is_a_workspace_member_can_change(self, workspace, project):
        admin = _person(workspace, project, MEMBER, ADMIN)
        sales = _group(workspace, "Sales")

        response = _link(_client(admin), workspace, project, sales)

        assert response.status_code == 201

    def test_a_workspace_guest_in_the_project_reads_but_cannot_change(self, workspace, project):
        guest = _person(workspace, project, GUEST, GUEST)
        client = _client(guest)
        sales = _group(workspace, "Sales")

        assert client.get(_url(workspace, project)).status_code == 200
        assert _link(client, workspace, project, sales).status_code == 403

    def test_a_user_outside_the_project_cannot_read_or_change(self, workspace, project):
        outsider = _client(_person(workspace))
        sales = _group(workspace, "Sales")

        assert outsider.get(_url(workspace, project)).status_code == 403
        assert _link(outsider, workspace, project, sales).status_code == 403

    def test_a_workspace_admin_who_is_not_in_the_project_cannot_change_it(self, workspace, project):
        outsider = _client(_person(workspace, ws_role=ADMIN))
        sales = _group(workspace, "Sales")

        assert _link(outsider, workspace, project, sales).status_code == 403
        assert not ProjectGroup.objects.filter(project=project).exists()

    def test_requests_without_an_api_key_are_refused(self, workspace, project):
        response = APIClient().get(_url(workspace, project))

        assert response.status_code == 401


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectMembersExposeGroups:
    def test_list_and_detail_carry_via_group_group_role_and_direct_role(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        through_group = _person(workspace)
        raised = _person(workspace, project, MEMBER, GUEST)
        _join(sales, through_group)
        _join(sales, raised)
        _link(api_key_client, workspace, project, sales, MEMBER)

        listed = api_key_client.get(_members_url(workspace, project))

        assert listed.status_code == 200
        by_id = {entry["id"]: entry for entry in listed.json()}
        assert (by_id[str(through_group.id)]["via_group"], by_id[str(through_group.id)]["group_role"]) == (True, MEMBER)
        assert by_id[str(through_group.id)]["direct_role"] is None
        assert (by_id[str(raised.id)]["via_group"], by_id[str(raised.id)]["group_role"]) == (False, MEMBER)
        assert by_id[str(raised.id)]["direct_role"] == GUEST

        row = ProjectMember.objects.get(project=project, member=through_group)
        detail = api_key_client.get(_members_url(workspace, project, f"{row.id}/"))
        assert detail.status_code == 200
        assert (detail.json()["via_group"], detail.json()["group_role"], detail.json()["direct_role"]) == (
            True,
            MEMBER,
            None,
        )

    def test_a_person_of_no_group_has_empty_group_fields(self, api_key_client, workspace, project, create_user):
        listed = api_key_client.get(_members_url(workspace, project))

        entry = next(e for e in listed.json() if e["id"] == str(create_user.id))
        assert (entry["via_group"], entry["group_role"], entry["direct_role"]) == (False, None, None)

    def test_lite_list_carries_the_group_fields(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace)
        _join(sales, ada)
        _link(api_key_client, workspace, project, sales, GUEST)

        response = api_key_client.get(
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/project-members-lite/"
        )

        assert response.status_code == 200
        entry = next(e for e in response.json()["results"] if e["id"] == str(ada.id))
        assert (entry["via_group"], entry["group_role"], entry["direct_role"]) == (True, GUEST, None)

    def test_group_fields_are_read_only_on_the_member_endpoints(self, api_key_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace)
        _join(sales, ada)
        _link(api_key_client, workspace, project, sales, MEMBER)
        row = ProjectMember.objects.get(project=project, member=ada)

        response = api_key_client.patch(
            _members_url(workspace, project, f"{row.id}/"),
            {"via_group": False, "group_role": None, "direct_role": GUEST},
            format="json",
        )

        assert response.status_code == 200, response.data
        row.refresh_from_db()
        assert row.via_group is True
        assert row.group_role == MEMBER
