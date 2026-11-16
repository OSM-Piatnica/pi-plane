# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Departments: user groups of kind "department", and the department of a workspace member."""

import pytest
from rest_framework.test import APIClient

from plane.db.models import GroupKind, GroupRole, GroupSource, User, UserGroup, UserGroupMember, WorkspaceMember

SLUG = "test-workspace"
GROUPS = f"/api/workspaces/{SLUG}/user-groups/"
DEPARTMENTS = f"/api/workspaces/{SLUG}/departments/"
MEMBERS = f"/api/workspaces/{SLUG}/members/"


def _person(workspace, email, role=15):
    user = User.objects.create(email=email, username=email, first_name=email.split("@")[0])
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _as(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _department(workspace, name, code="", **extra):
    return UserGroup.objects.create(workspace=workspace, name=name, code=code, kind=GroupKind.DEPARTMENT, **extra)


def _member(workspace, user):
    return WorkspaceMember.objects.get(workspace=workspace, member=user)


def _department_url(workspace, user):
    return f"{MEMBERS}{_member(workspace, user).id}/department/"


def _in_group(group, user):
    return UserGroupMember.objects.filter(group=group, user=user).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestDepartmentDictionary:
    def test_an_admin_creates_departments_with_code_colour_and_order(self, session_client, workspace):
        first = session_client.post(
            GROUPS, {"name": "Marketing", "kind": "department", "code": " rm ", "color": "#3f76ff"}, format="json"
        )
        second = session_client.post(GROUPS, {"name": "Quality", "kind": "department", "code": "QA"}, format="json")

        assert first.status_code == 201 and second.status_code == 201
        assert first.data["kind"] == "department" and first.data["code"] == "RM"
        assert first.data["color"] == "#3f76ff" and first.data["is_active"] is True
        assert second.data["sort_order"] > first.data["sort_order"]

    def test_a_group_is_a_plain_group_unless_said_otherwise(self, session_client, workspace):
        response = session_client.post(GROUPS, {"name": "Sales"}, format="json")

        assert response.status_code == 201
        assert response.data["kind"] == "group" and response.data["code"] == ""

    def test_a_code_is_unique_among_the_departments_of_a_workspace(self, session_client, workspace):
        marketing = _department(workspace, "Marketing", "RM")
        quality = _department(workspace, "Quality", "QA")
        # A plain group does not take a code away from the departments
        UserGroup.objects.create(workspace=workspace, name="Sales", code="SL")

        duplicate = session_client.post(GROUPS, {"name": "Other", "kind": "department", "code": "rm"}, format="json")
        renamed = session_client.patch(f"{GROUPS}{quality.id}/", {"code": "RM"}, format="json")
        free = session_client.post(GROUPS, {"name": "Selling", "kind": "department", "code": "SL"}, format="json")
        unchanged = session_client.patch(f"{GROUPS}{marketing.id}/", {"code": "RM", "color": "#fff"}, format="json")

        assert duplicate.status_code == 409 and renamed.status_code == 409
        assert free.status_code == 201 and unchanged.status_code == 200

    def test_departments_without_a_code_do_not_collide(self, session_client, workspace):
        first = session_client.post(GROUPS, {"name": "One", "kind": "department"}, format="json")
        second = session_client.post(GROUPS, {"name": "Two", "kind": "department"}, format="json")

        assert first.status_code == 201 and second.status_code == 201

    def test_a_colour_has_to_be_a_hex_value(self, session_client, workspace):
        response = session_client.post(GROUPS, {"name": "Red", "kind": "department", "color": "red"}, format="json")

        assert response.status_code == 400

    def test_the_list_filters_by_kind_and_orders_departments(self, session_client, workspace):
        _department(workspace, "Zebra", "Z", sort_order=10)
        _department(workspace, "Alpha", "A", sort_order=20)
        UserGroup.objects.create(workspace=workspace, name="Sales")

        departments = session_client.get(GROUPS, {"kind": "department"})
        groups = session_client.get(GROUPS, {"kind": "group"})
        everything = session_client.get(GROUPS)
        unknown = session_client.get(GROUPS, {"kind": "team"})

        assert [row["name"] for row in departments.data] == ["Zebra", "Alpha"]
        assert [row["name"] for row in groups.data] == ["Sales"]
        assert len(everything.data) == 3
        assert unknown.status_code == 400

    def test_only_a_workspace_admin_changes_what_makes_a_department(self, session_client, workspace):
        lead = _person(workspace, "lead@example.com")
        top = UserGroup.objects.create(workspace=workspace, name="Sales")
        UserGroupMember.objects.create(workspace=workspace, group=top, user=lead, role=GroupRole.ADMIN)
        client = _as(lead)

        created = client.post(GROUPS, {"name": "Poland", "parent": str(top.id), "kind": "department"}, format="json")
        changed = client.patch(f"{GROUPS}{top.id}/", {"kind": "department"}, format="json")
        renamed = client.patch(f"{GROUPS}{top.id}/", {"name": "Selling"}, format="json")

        assert created.status_code == 403 and changed.status_code == 403
        assert renamed.status_code == 200

    def test_a_mirrored_group_can_be_made_a_department(self, session_client, workspace):
        mirrored = UserGroup.objects.create(
            workspace=workspace, name="Department: IT", source=GroupSource.ENTRA, external_id="department:it"
        )

        response = session_client.patch(f"{GROUPS}{mirrored.id}/", {"kind": "department", "code": "IT"}, format="json")
        renamed = session_client.patch(f"{GROUPS}{mirrored.id}/", {"name": "IT"}, format="json")

        assert response.status_code == 200 and response.data["kind"] == "department"
        assert renamed.status_code == 400

    def test_the_picker_list_is_open_to_guests_and_leaves_out_what_is_switched_off(self, session_client, workspace):
        _department(workspace, "Marketing", "RM", sort_order=2)
        _department(workspace, "Quality", "QA", sort_order=1)
        _department(workspace, "Closed", "CL", is_active=False)
        UserGroup.objects.create(workspace=workspace, name="Sales")
        guest = _person(workspace, "guest@example.com", role=5)
        outsider = User.objects.create(email="out@example.com", username="out")

        response = _as(guest).get(DEPARTMENTS)

        assert response.status_code == 200
        assert [row["code"] for row in response.data] == ["QA", "RM"]
        assert _as(outsider).get(DEPARTMENTS).status_code == 403


@pytest.mark.contract
@pytest.mark.django_db
class TestMemberDepartment:
    def test_a_member_sets_their_own_department_and_joins_its_group(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing = _department(workspace, "Marketing", "RM")

        response = _as(pat).patch(_department_url(workspace, pat), {"department": str(marketing.id)}, format="json")

        assert response.status_code == 200 and str(response.data["department"]) == str(marketing.id)
        assert _member(workspace, pat).department_id == marketing.id
        assert _in_group(marketing, pat)

    def test_a_guest_sets_their_own_department(self, session_client, workspace):
        guest = _person(workspace, "guest@example.com", role=5)
        marketing = _department(workspace, "Marketing", "RM")

        response = _as(guest).patch(_department_url(workspace, guest), {"department": str(marketing.id)}, format="json")

        assert response.status_code == 200
        assert _member(workspace, guest).department_id == marketing.id

    def test_a_member_cannot_set_the_department_of_another_person(self, session_client, workspace):
        pat, ola = _person(workspace, "pat@example.com"), _person(workspace, "ola@example.com")
        marketing = _department(workspace, "Marketing", "RM")

        response = _as(pat).patch(_department_url(workspace, ola), {"department": str(marketing.id)}, format="json")

        assert response.status_code == 403
        assert _member(workspace, ola).department_id is None

    def test_an_admin_moves_a_person_between_departments(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing, quality = _department(workspace, "Marketing", "RM"), _department(workspace, "Quality", "QA")
        url = _department_url(workspace, pat)

        session_client.patch(url, {"department": str(marketing.id)}, format="json")
        moved = session_client.patch(url, {"department": str(quality.id)}, format="json")

        assert moved.status_code == 200
        assert _member(workspace, pat).department_id == quality.id
        assert _in_group(quality, pat) and not _in_group(marketing, pat)

        cleared = session_client.patch(url, {"department": None}, format="json")

        assert cleared.status_code == 200 and cleared.data["department"] is None
        assert _member(workspace, pat).department_id is None
        assert not _in_group(quality, pat)

    def test_only_an_active_department_of_the_workspace_can_be_chosen(self, session_client, workspace, create_user):
        pat = _person(workspace, "pat@example.com")
        plain = UserGroup.objects.create(workspace=workspace, name="Sales")
        closed = _department(workspace, "Closed", "CL", is_active=False)
        from plane.db.models import Workspace

        other = Workspace.objects.create(name="Other", slug="other", owner=create_user)
        foreign = _department(other, "Foreign", "FR")
        url = _department_url(workspace, pat)

        for group in (plain, closed, foreign):
            response = session_client.patch(url, {"department": str(group.id)}, format="json")
            assert response.status_code == 400, group.name
        assert session_client.patch(url, {}, format="json").status_code == 400
        assert _member(workspace, pat).department_id is None

    def test_a_mirrored_department_is_only_for_the_people_the_provider_put_in_it(self, session_client, workspace):
        pat, ola = _person(workspace, "pat@example.com"), _person(workspace, "ola@example.com")
        mirrored = _department(workspace, "Department: IT", "IT", source=GroupSource.ENTRA, external_id="department:it")
        UserGroupMember.objects.create(workspace=workspace, group=mirrored, user=pat, managed_externally=True)
        local = _department(workspace, "Marketing", "RM")

        refused = session_client.patch(_department_url(workspace, ola), {"department": str(mirrored.id)}, format="json")
        accepted = session_client.patch(
            _department_url(workspace, pat), {"department": str(mirrored.id)}, format="json"
        )
        # Moving on to a local department leaves the provider's membership alone
        session_client.patch(_department_url(workspace, pat), {"department": str(local.id)}, format="json")

        assert refused.status_code == 400 and accepted.status_code == 200
        assert _member(workspace, pat).department_id == local.id
        assert _in_group(mirrored, pat) and _in_group(local, pat)

    def test_the_members_list_carries_the_department(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing = _department(workspace, "Marketing", "RM")
        session_client.patch(_department_url(workspace, pat), {"department": str(marketing.id)}, format="json")

        rows = {row["member"]["id"]: row for row in session_client.get(MEMBERS).data}
        me = session_client.get(f"/api/workspaces/{SLUG}/workspace-members/me/")

        assert str(rows[pat.id]["department"]) == str(marketing.id)
        assert "department" in me.data and me.data["department"] is None

    def test_joining_a_department_group_gives_a_person_without_one_that_department(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing, quality = _department(workspace, "Marketing", "RM"), _department(workspace, "Quality", "QA")

        session_client.post(f"{GROUPS}{marketing.id}/members/", {"user_id": str(pat.id)}, format="json")
        # A second department group by hand does not replace the one the person has
        session_client.post(f"{GROUPS}{quality.id}/members/", {"user_id": str(pat.id)}, format="json")

        assert _member(workspace, pat).department_id == marketing.id

        session_client.delete(f"{GROUPS}{marketing.id}/members/{pat.id}/")

        assert _member(workspace, pat).department_id is None

    def test_a_department_that_is_deleted_or_turned_into_a_group_leaves_its_people(self, session_client, workspace):
        pat, ola = _person(workspace, "pat@example.com"), _person(workspace, "ola@example.com")
        marketing, quality = _department(workspace, "Marketing", "RM"), _department(workspace, "Quality", "QA")
        session_client.patch(_department_url(workspace, pat), {"department": str(marketing.id)}, format="json")
        session_client.patch(_department_url(workspace, ola), {"department": str(quality.id)}, format="json")

        turned = session_client.patch(f"{GROUPS}{marketing.id}/", {"kind": "group"}, format="json")
        deleted = session_client.delete(f"{GROUPS}{quality.id}/")

        assert turned.status_code == 200 and deleted.status_code == 204
        assert _member(workspace, pat).department_id is None
        assert _member(workspace, ola).department_id is None
        # Still a member of what is now a plain group
        assert _in_group(marketing, pat)

    def test_switching_a_department_off_keeps_it_on_its_people(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing = _department(workspace, "Marketing", "RM")
        session_client.patch(_department_url(workspace, pat), {"department": str(marketing.id)}, format="json")

        response = session_client.patch(f"{GROUPS}{marketing.id}/", {"is_active": False}, format="json")

        assert response.status_code == 200 and response.data["is_active"] is False
        assert _member(workspace, pat).department_id == marketing.id
