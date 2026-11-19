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

    def test_a_group_that_becomes_a_department_gives_it_to_its_members_without_one(self, session_client, workspace):
        pat, ola, eve = (
            _person(workspace, "pat@example.com"),
            _person(workspace, "ola@example.com"),
            _person(workspace, "eve@example.com"),
        )
        quality = _department(workspace, "Quality", "QA")
        WorkspaceMember.objects.filter(workspace=workspace, member=ola).update(department=quality)
        UserGroupMember.objects.create(workspace=workspace, group=quality, user=ola)
        sales = UserGroup.objects.create(workspace=workspace, name="Sales")
        below = UserGroup.objects.create(workspace=workspace, name="Poland", parent=sales)
        for person in (pat, ola):
            UserGroupMember.objects.create(workspace=workspace, group=sales, user=person)
        UserGroupMember.objects.create(workspace=workspace, group=below, user=eve)

        response = session_client.patch(f"{GROUPS}{sales.id}/", {"kind": "department", "code": "SL"}, format="json")

        assert response.status_code == 200
        assert _member(workspace, pat).department_id == sales.id
        # someone with a department keeps it, and the members of a group below are not direct members
        assert _member(workspace, ola).department_id == quality.id
        assert _member(workspace, eve).department_id is None

        back = session_client.patch(f"{GROUPS}{sales.id}/", {"kind": "group"}, format="json")

        assert back.status_code == 200
        assert _member(workspace, pat).department_id is None
        assert _member(workspace, ola).department_id == quality.id

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
class TestMemberDepartment:
    def test_an_admin_sets_a_department_and_the_person_joins_its_group(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        marketing = _department(workspace, "Marketing", "RM")

        response = session_client.patch(
            _department_url(workspace, pat), {"department": str(marketing.id)}, format="json"
        )

        assert response.status_code == 200 and str(response.data["department"]) == str(marketing.id)
        assert _member(workspace, pat).department_id == marketing.id
        assert _in_group(marketing, pat)

    def test_an_admin_sets_their_own_department(self, session_client, workspace, create_user):
        marketing = _department(workspace, "Marketing", "RM")

        response = session_client.patch(
            _department_url(workspace, create_user), {"department": str(marketing.id)}, format="json"
        )

        assert response.status_code == 200
        assert _member(workspace, create_user).department_id == marketing.id

    @pytest.mark.parametrize("role", [15, 5])
    def test_members_and_guests_cannot_set_their_own_department(self, session_client, workspace, role):
        person = _person(workspace, "pat@example.com", role=role)
        marketing = _department(workspace, "Marketing", "RM")

        response = _as(person).patch(
            _department_url(workspace, person), {"department": str(marketing.id)}, format="json"
        )

        assert response.status_code == 403
        assert _member(workspace, person).department_id is None
        assert not _in_group(marketing, person)

    def test_a_member_cannot_get_into_a_project_through_the_department_endpoint(
        self, session_client, workspace, create_user
    ):
        from plane.db.models import Project, ProjectGroup, ProjectMember

        pat = _person(workspace, "pat@example.com")
        finance = _department(workspace, "Finance", "FI")
        project = Project.objects.create(
            name="Budget", identifier="BUD", workspace=workspace, created_by=create_user, network=0
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
        ProjectGroup.objects.create(project=project, workspace=workspace, group=finance)

        response = _as(pat).patch(_department_url(workspace, pat), {"department": str(finance.id)}, format="json")

        assert response.status_code == 403
        assert not ProjectMember.objects.filter(project=project, member=pat, is_active=True).exists()
        # The same department given by a workspace admin does give the project: that is why it is theirs to give
        session_client.patch(_department_url(workspace, pat), {"department": str(finance.id)}, format="json")
        assert ProjectMember.objects.filter(project=project, member=pat, is_active=True).exists()

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

        refused = session_client.patch(_department_url(workspace, ola), {"department": str(mirrored.id)}, format="json")
        accepted = session_client.patch(
            _department_url(workspace, pat), {"department": str(mirrored.id)}, format="json"
        )

        assert refused.status_code == 400 and accepted.status_code == 200
        assert _member(workspace, pat).department_id == mirrored.id

    def test_a_department_from_the_provider_cannot_be_changed_or_cleared_here(self, session_client, workspace):
        pat = _person(workspace, "pat@example.com")
        mirrored = _department(workspace, "Department: IT", "IT", source=GroupSource.ENTRA, external_id="department:it")
        UserGroupMember.objects.create(workspace=workspace, group=mirrored, user=pat, managed_externally=True)
        WorkspaceMember.objects.filter(workspace=workspace, member=pat).update(department=mirrored)
        local = _department(workspace, "Marketing", "RM")
        url = _department_url(workspace, pat)

        changed = session_client.patch(url, {"department": str(local.id)}, format="json")
        cleared = session_client.patch(url, {"department": None}, format="json")

        assert changed.status_code == 400 and cleared.status_code == 400
        assert "identity provider" in changed.data["error"]
        assert _member(workspace, pat).department_id == mirrored.id
        assert _in_group(mirrored, pat) and not _in_group(local, pat)

    def test_changing_the_department_keeps_hand_made_and_group_admin_memberships(self, session_client, workspace):
        pat, ola = _person(workspace, "pat@example.com"), _person(workspace, "ola@example.com")
        marketing, quality, sales = (
            _department(workspace, "Marketing", "RM"),
            _department(workspace, "Quality", "QA"),
            _department(workspace, "Sales", "SL"),
        )
        # Pat is made the group admin of Marketing after getting it as department
        session_client.patch(_department_url(workspace, pat), {"department": str(marketing.id)}, format="json")
        session_client.patch(f"{GROUPS}{marketing.id}/members/{pat.id}/", {"role": GroupRole.ADMIN}, format="json")
        # Ola was put into Quality by hand before it became her department
        UserGroupMember.objects.create(workspace=workspace, group=quality, user=ola)
        session_client.patch(_department_url(workspace, ola), {"department": str(quality.id)}, format="json")

        session_client.patch(_department_url(workspace, pat), {"department": str(sales.id)}, format="json")
        session_client.patch(_department_url(workspace, ola), {"department": str(sales.id)}, format="json")

        assert _member(workspace, pat).department_id == sales.id
        assert UserGroupMember.objects.get(group=marketing, user=pat).role == GroupRole.ADMIN
        assert _member(workspace, ola).department_id == sales.id
        assert _in_group(quality, ola)

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
