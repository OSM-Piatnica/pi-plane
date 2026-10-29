# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""User groups: nesting, membership in several groups, and what a group admin may do."""

import pytest
from rest_framework.test import APIClient

from plane.db.models import GroupRole, GroupSource, User, UserGroup, UserGroupMember, WorkspaceMember
from plane.utils.user_groups import group_ids_of_user, member_user_ids

SLUG = "test-workspace"
GROUPS = f"/api/workspaces/{SLUG}/user-groups/"


def _group_url(group):
    return f"{GROUPS}{group.id}/"


def _members_url(group):
    return f"{GROUPS}{group.id}/members/"


def _person(workspace, email, role=15):
    user = User.objects.create(email=email, first_name=email.split("@")[0])
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _as(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _group(workspace, name, parent=None, **extra):
    return UserGroup.objects.create(workspace=workspace, name=name, parent=parent, **extra)


def _join(group, user, role=GroupRole.MEMBER):
    return UserGroupMember.objects.create(workspace=group.workspace, group=group, user=user, role=role)


@pytest.mark.contract
@pytest.mark.django_db
class TestGroupsAsWorkspaceAdmin:
    def test_a_workspace_admin_creates_nested_groups_and_deletes_them(self, session_client, workspace):
        top = session_client.post(GROUPS, {"name": "Sales"}, format="json")
        child = session_client.post(GROUPS, {"name": "Poland", "parent": top.data["id"]}, format="json")

        assert top.status_code == 201 and child.status_code == 201
        assert child.data["parent"] == top.data["id"]
        assert session_client.delete(f"{GROUPS}{child.data['id']}/").status_code == 204
        assert session_client.delete(f"{GROUPS}{top.data['id']}/").status_code == 204
        assert UserGroup.objects.filter(workspace=workspace).count() == 0

    def test_a_group_with_subgroups_cannot_be_deleted(self, session_client, workspace):
        top = _group(workspace, "Sales")
        _group(workspace, "Poland", parent=top)

        response = session_client.delete(_group_url(top))

        assert response.status_code == 400
        assert UserGroup.objects.filter(pk=top.pk).exists()

    def test_names_are_unique_among_siblings_only(self, session_client, workspace):
        sales = _group(workspace, "Sales")
        ops = _group(workspace, "Operations")
        _group(workspace, "Team", parent=sales)

        assert session_client.post(GROUPS, {"name": "sales"}, format="json").status_code == 409
        assert session_client.post(GROUPS, {"name": "Team", "parent": str(sales.id)}, format="json").status_code == 409
        assert session_client.post(GROUPS, {"name": "Team", "parent": str(ops.id)}, format="json").status_code == 201

    def test_a_group_cannot_be_moved_under_itself_or_its_own_subgroup(self, session_client, workspace):
        top = _group(workspace, "Top")
        middle = _group(workspace, "Middle", parent=top)
        bottom = _group(workspace, "Bottom", parent=middle)

        under_bottom = session_client.patch(_group_url(top), {"parent": str(bottom.id)}, format="json")
        under_itself = session_client.patch(_group_url(top), {"parent": str(top.id)}, format="json")

        assert under_bottom.status_code == 400
        assert under_itself.status_code == 400
        top.refresh_from_db()
        assert top.parent_id is None

    def test_nesting_is_limited_in_depth(self, session_client, workspace):
        parent = None
        for level in range(10):
            parent = _group(workspace, f"Level {level}", parent=parent)

        response = session_client.post(GROUPS, {"name": "Too deep", "parent": str(parent.id)}, format="json")

        assert response.status_code == 400

    def test_one_person_can_be_in_several_groups_and_belongs_to_the_groups_above(self, session_client, workspace):
        member = _person(workspace, "ada@example.com")
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        support = _group(workspace, "Support")

        for group in (poland, support):
            response = session_client.post(_members_url(group), {"user_id": str(member.id)}, format="json")
            assert response.status_code == 201, response.data

        assert group_ids_of_user(workspace.id, member.id) == {sales.id, poland.id, support.id}
        assert member_user_ids(workspace.id, [sales.id]) == {member.id}
        nested = session_client.get(_members_url(sales) + "?nested=true")
        assert [entry["user"]["id"] for entry in nested.data] == [str(member.id)]
        assert session_client.get(_members_url(sales)).data == []

    def test_only_workspace_members_can_join_and_twice_is_a_conflict(self, session_client, workspace):
        outsider = User.objects.create(email="out@example.com")
        member = _person(workspace, "in@example.com")
        group = _group(workspace, "Sales")

        assert session_client.post(_members_url(group), {"user_id": str(outsider.id)}, format="json").status_code == 400
        assert session_client.post(_members_url(group), {"user_id": str(member.id)}, format="json").status_code == 201
        assert session_client.post(_members_url(group), {"user_id": str(member.id)}, format="json").status_code == 409

    def test_removing_a_person_takes_them_out_of_the_group(self, session_client, workspace):
        member = _person(workspace, "ada@example.com")
        group = _group(workspace, "Sales")
        _join(group, member)

        response = session_client.delete(f"{_members_url(group)}{member.id}/")

        assert response.status_code == 204
        assert member_user_ids(workspace.id, [group.id]) == set()


@pytest.mark.contract
@pytest.mark.django_db
class TestGroupAdmin:
    def _setup(self, workspace):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        other = _group(workspace, "Operations")
        boss = _person(workspace, "boss@example.com")
        _join(sales, boss, GroupRole.ADMIN)
        return sales, poland, other, boss

    def test_a_group_admin_manages_members_of_their_group_and_the_ones_below(self, workspace):
        sales, poland, other, boss = self._setup(workspace)
        newcomer = _person(workspace, "new@example.com")
        client = _as(boss)

        assert client.post(_members_url(sales), {"user_id": str(newcomer.id)}, format="json").status_code == 201
        assert client.post(_members_url(poland), {"user_id": str(newcomer.id)}, format="json").status_code == 201
        assert (
            client.patch(f"{_members_url(poland)}{newcomer.id}/", {"role": GroupRole.ADMIN}, format="json").status_code
            == 200
        )
        assert client.delete(f"{_members_url(poland)}{newcomer.id}/").status_code == 204

    def test_a_group_admin_cannot_touch_other_groups(self, workspace):
        sales, poland, other, boss = self._setup(workspace)
        newcomer = _person(workspace, "new@example.com")
        client = _as(boss)

        assert client.post(_members_url(other), {"user_id": str(newcomer.id)}, format="json").status_code == 403
        assert client.patch(_group_url(other), {"description": "x"}, format="json").status_code == 403
        assert client.delete(_group_url(other)).status_code == 403

    def test_a_group_admin_creates_and_deletes_subgroups_but_not_top_level_groups(self, workspace):
        sales, poland, other, boss = self._setup(workspace)
        client = _as(boss)

        created = client.post(GROUPS, {"name": "Germany", "parent": str(sales.id)}, format="json")
        deeper = client.post(GROUPS, {"name": "Berlin", "parent": created.data["id"]}, format="json")

        assert created.status_code == 201 and deeper.status_code == 201
        assert client.post(GROUPS, {"name": "Marketing"}, format="json").status_code == 403
        assert client.delete(f"{GROUPS}{deeper.data['id']}/").status_code == 204
        # The group they administer is removed by someone above them
        assert client.delete(_group_url(sales)).status_code == 403

    def test_a_group_admin_cannot_move_a_group_out_of_their_tree(self, workspace):
        sales, poland, other, boss = self._setup(workspace)

        response = _as(boss).patch(_group_url(poland), {"parent": str(other.id)}, format="json")

        assert response.status_code == 403
        poland.refresh_from_db()
        assert poland.parent_id == sales.id

    def test_an_ordinary_member_and_a_guest_cannot_change_groups(self, workspace):
        member = _person(workspace, "member@example.com")
        guest = _person(workspace, "guest@example.com", role=5)
        group = _group(workspace, "Sales")

        assert _as(member).post(GROUPS, {"name": "Mine"}, format="json").status_code == 403
        assert _as(member).patch(_group_url(group), {"name": "Renamed"}, format="json").status_code == 403
        assert _as(guest).get(GROUPS).status_code == 403

    def test_being_admin_of_a_group_does_not_make_someone_a_workspace_admin(self, workspace):
        sales, poland, other, boss = self._setup(workspace)

        assert _as(boss).get(f"/api/workspaces/{SLUG}/invitations/").status_code in (403, 404)

    def test_the_list_tells_what_the_requester_may_do(self, workspace):
        sales, poland, other, boss = self._setup(workspace)

        rows = {row["name"]: row for row in _as(boss).get(GROUPS).data}

        assert rows["Sales"]["can_manage"] and not rows["Sales"]["can_delete"]
        assert rows["Poland"]["can_manage"] and rows["Poland"]["can_delete"]
        assert not rows["Operations"]["can_manage"]


@pytest.mark.contract
@pytest.mark.django_db
class TestExternalGroups:
    def test_members_and_names_of_a_group_managed_by_the_provider_are_read_only(self, session_client, workspace):
        external = _group(workspace, "Entra Sales", source=GroupSource.ENTRA, external_id="abc")
        member = _person(workspace, "ada@example.com")

        assert (
            session_client.post(_members_url(external), {"user_id": str(member.id)}, format="json").status_code == 400
        )
        assert session_client.patch(_group_url(external), {"name": "Renamed"}, format="json").status_code == 400

    def test_an_external_group_can_be_placed_under_a_local_one(self, session_client, workspace):
        external = _group(workspace, "Entra Sales", source=GroupSource.ENTRA, external_id="abc")
        local = _group(workspace, "All sales")

        response = session_client.patch(_group_url(external), {"parent": str(local.id)}, format="json")

        assert response.status_code == 200, response.data
        external.refresh_from_db()
        assert external.parent_id == local.id

    def test_nothing_can_be_put_under_an_external_group(self, session_client, workspace):
        external = _group(workspace, "Entra Sales", source=GroupSource.ENTRA, external_id="abc")

        response = session_client.post(GROUPS, {"name": "Child", "parent": str(external.id)}, format="json")

        assert response.status_code == 400
