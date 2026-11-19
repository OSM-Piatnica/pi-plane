# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Departments: user groups of kind "department", one active department per person, managed by workspace admins."""

import pytest
from rest_framework.test import APIClient

from plane.db.models import GroupKind, GroupRole, GroupSource, User, UserGroup, UserGroupMember, WorkspaceMember

SLUG = "test-workspace"
GROUPS = f"/api/workspaces/{SLUG}/user-groups/"
DEPARTMENTS = f"/api/workspaces/{SLUG}/departments/"
DEPARTMENT_MEMBERS = f"/api/workspaces/{SLUG}/departments/members/"


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

    def test_a_group_admin_cannot_manage_a_department(self, session_client, workspace):
        lead, pat = _person(workspace, "lead@example.com"), _person(workspace, "pat@example.com")
        top = UserGroup.objects.create(workspace=workspace, name="Operations")
        UserGroupMember.objects.create(workspace=workspace, group=top, user=lead, role=GroupRole.ADMIN)
        # A department under the group the lead rules, and one the lead is the group admin of
        nested = _department(workspace, "Logistics", "LG", parent=top)
        own = _department(workspace, "Marketing", "RM")
        UserGroupMember.objects.create(workspace=workspace, group=own, user=lead, role=GroupRole.ADMIN)
        UserGroupMember.objects.create(workspace=workspace, group=own, user=pat)
        plain = UserGroup.objects.create(workspace=workspace, name="Drivers", parent=top)
        client = _as(lead)

        for department in (nested, own):
            url = f"{GROUPS}{department.id}/"
            assert client.patch(url, {"name": "Renamed"}, format="json").status_code == 403
            assert client.patch(url, {"parent": None}, format="json").status_code == 403
            assert client.patch(url, {"kind": "group"}, format="json").status_code == 403
            assert client.post(f"{url}members/", {"user_id": str(pat.id)}, format="json").status_code in (403, 409)
            assert client.post(GROUPS, {"name": "Sub", "parent": str(department.id)}, format="json").status_code == 403
            assert client.delete(url).status_code == 403
        assert client.delete(f"{GROUPS}{own.id}/members/{pat.id}/").status_code == 403
        listed = {row["id"]: row for row in client.get(GROUPS).data}
        assert not listed[str(nested.id)]["can_manage"] and not listed[str(nested.id)]["can_delete"]
        assert not listed[str(own.id)]["can_manage"]
        # The ordinary groups the lead rules stay theirs
        assert client.patch(f"{GROUPS}{plain.id}/", {"name": "Couriers"}, format="json").status_code == 200
        assert client.delete(f"{GROUPS}{plain.id}/").status_code == 204
        assert UserGroup.objects.filter(pk=nested.pk, name="Logistics").exists()
        assert _in_group(own, pat)

    def test_a_group_whose_members_have_another_department_cannot_become_one(self, session_client, workspace):
        pat, ola = _person(workspace, "pat@example.com"), _person(workspace, "ola@example.com")
        quality = _department(workspace, "Quality", "QA")
        UserGroupMember.objects.create(workspace=workspace, group=quality, user=ola)
        sales = UserGroup.objects.create(workspace=workspace, name="Sales")
        for person in (pat, ola):
            UserGroupMember.objects.create(workspace=workspace, group=sales, user=person)

        refused = session_client.patch(f"{GROUPS}{sales.id}/", {"kind": "department", "code": "SL"}, format="json")

        assert refused.status_code == 400
        assert "ola" in refused.data["error"] and "Quality" in refused.data["error"]
        assert UserGroup.objects.get(pk=sales.pk).kind == GroupKind.GROUP

        UserGroupMember.objects.filter(group=quality, user=ola).delete()
        accepted = session_client.patch(f"{GROUPS}{sales.id}/", {"kind": "department", "code": "SL"}, format="json")

        assert accepted.status_code == 200 and accepted.data["kind"] == "department"

    def test_a_department_whose_members_have_another_cannot_be_switched_on(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        quality = _department(workspace, "Quality", "QA")
        closed = _department(workspace, "Closed", "CL", is_active=False)
        for group in (quality, closed):
            UserGroupMember.objects.create(workspace=workspace, group=group, user=pat)

        refused = session_client.patch(f"{GROUPS}{closed.id}/", {"is_active": True}, format="json")
        # Switching off and back on a department nobody else claims is fine
        off = session_client.patch(f"{GROUPS}{quality.id}/", {"is_active": False}, format="json")
        on = session_client.patch(f"{GROUPS}{closed.id}/", {"is_active": True}, format="json")

        assert refused.status_code == 400 and "Quality" in refused.data["error"]
        assert off.status_code == 200 and on.status_code == 200

    def test_a_code_that_is_too_long_once_upper_cased_is_refused(self, session_client, workspace):
        # "ß" is one character, its upper case "SS" two: 16 of them become 32
        response = session_client.post(
            GROUPS, {"name": "Street", "kind": "department", "code": "ß" * 16}, format="json"
        )
        padded = session_client.post(GROUPS, {"name": "Padded", "kind": "department", "code": "  rm  "}, format="json")

        assert response.status_code == 400 and "code" in response.data
        assert padded.status_code == 201 and padded.data["code"] == "RM"

    def test_a_code_taken_by_a_concurrent_request_is_a_conflict(self, session_client, workspace):
        from unittest import mock

        _department(workspace, "Marketing", "RM")
        quality = _department(workspace, "Quality", "QA")
        # The check passes as if the other request had not written yet; the database still refuses
        with mock.patch("plane.app.views.workspace.user_group.code_taken", return_value=False):
            created = session_client.post(GROUPS, {"name": "Brand", "kind": "department", "code": "RM"}, format="json")
            changed = session_client.patch(f"{GROUPS}{quality.id}/", {"code": "RM"}, format="json")

        assert created.status_code == 409 and changed.status_code == 409
        assert created.data["error"] == changed.data["error"] == "Another department already has this code."
        assert UserGroup.objects.filter(workspace=workspace, code="RM").count() == 1

    def test_a_mirrored_group_can_be_made_a_department(self, session_client, workspace):
        mirrored = UserGroup.objects.create(
            workspace=workspace, name="Department: IT", source=GroupSource.ENTRA, external_id="department:it"
        )

        response = session_client.patch(f"{GROUPS}{mirrored.id}/", {"kind": "department", "code": "IT"}, format="json")
        renamed = session_client.patch(f"{GROUPS}{mirrored.id}/", {"name": "IT"}, format="json")

        assert response.status_code == 200 and response.data["kind"] == "department"
        assert renamed.status_code == 400

    def test_a_group_admin_still_manages_a_group_below_a_department(self, session_client, workspace):
        pat, ola = _person(workspace, "pat@example.com"), _person(workspace, "ola@example.com")
        finance = _department(workspace, "Finance", "FI")
        team = UserGroup.objects.create(workspace=workspace, name="Team", parent=finance)
        UserGroupMember.objects.create(workspace=workspace, group=team, user=pat, role=GroupRole.ADMIN)

        added = _as(pat).post(f"{GROUPS}{team.id}/members/", {"user_id": str(ola.id)}, format="json")

        assert added.status_code == 201

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
class TestDepartmentMembers:
    def test_an_admin_adds_a_person_to_one_department_only(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing, quality = _department(workspace, "Marketing", "RM"), _department(workspace, "Quality", "QA")
        closed = _department(workspace, "Closed", "CL", is_active=False)

        first = session_client.post(f"{GROUPS}{marketing.id}/members/", {"user_id": str(pat.id)}, format="json")
        second = session_client.post(f"{GROUPS}{quality.id}/members/", {"user_id": str(pat.id)}, format="json")
        switched_off = session_client.post(f"{GROUPS}{closed.id}/members/", {"user_id": str(pat.id)}, format="json")

        assert first.status_code == 201
        assert second.status_code == 409 and "Marketing" in second.data["error"]
        assert switched_off.status_code == 201
        assert not _in_group(quality, pat)

        # Moving a person is taking them out of one department and putting them in the other
        removed = session_client.delete(f"{GROUPS}{marketing.id}/members/{pat.id}/")
        moved = session_client.post(f"{GROUPS}{quality.id}/members/", {"user_id": str(pat.id)}, format="json")

        assert removed.status_code == 204 and moved.status_code == 201

    @pytest.mark.parametrize("role", [15, 5])
    def test_members_and_guests_cannot_join_a_department(self, session_client, workspace, role):
        person = _person(workspace, "pat@example.com", role=role)
        marketing = _department(workspace, "Marketing", "RM")

        response = _as(person).post(f"{GROUPS}{marketing.id}/members/", {"user_id": str(person.id)}, format="json")

        assert response.status_code == 403
        assert not _in_group(marketing, person)

    def test_who_works_where_is_derived_from_the_department_groups(self, session_client, workspace):
        pat, ola = _person(workspace, "pat@example.com"), _person(workspace, "ola@example.com")
        guest = _person(workspace, "guest@example.com", role=5)
        marketing = _department(workspace, "Marketing", "RM")
        closed = _department(workspace, "Closed", "CL", is_active=False)
        team = UserGroup.objects.create(workspace=workspace, name="Team", parent=marketing)
        UserGroupMember.objects.create(workspace=workspace, group=marketing, user=pat)
        UserGroupMember.objects.create(workspace=workspace, group=marketing, user=guest)
        UserGroupMember.objects.create(workspace=workspace, group=closed, user=ola)
        UserGroupMember.objects.create(workspace=workspace, group=team, user=ola)

        everyone = _as(pat).get(DEPARTMENT_MEMBERS)
        own = _as(guest).get(DEPARTMENT_MEMBERS)

        assert everyone.status_code == 200
        assert everyone.data == {str(pat.id): str(marketing.id), str(guest.id): str(marketing.id)}
        # A guest only learns their own department
        assert own.data == {str(guest.id): str(marketing.id)}

    def test_the_members_list_carries_no_department_field(self, session_client, workspace):
        response = session_client.get(f"/api/workspaces/{SLUG}/members/")

        assert response.status_code == 200
        assert all("department" not in row for row in response.data)

    def test_a_deleted_department_is_nobodys(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing = _department(workspace, "Marketing", "RM")
        UserGroupMember.objects.create(workspace=workspace, group=marketing, user=pat)

        assert session_client.delete(f"{GROUPS}{marketing.id}/").status_code == 204

        assert session_client.get(DEPARTMENT_MEMBERS).data == {}
