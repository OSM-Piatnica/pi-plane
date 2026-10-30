# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""User groups as members of a project: who gets in, with which role, and what the member endpoints still do."""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    Project,
    ProjectGroup,
    ProjectMember,
    State,
    User,
    UserGroup,
    UserGroupMember,
    Workspace,
    WorkspaceMember,
)
from plane.utils.project_groups import reconcile_project, reconcile_user

ADMIN, MEMBER, GUEST = 20, 15, 5
SLUG = "test-workspace"


@pytest.fixture(autouse=True)
def _no_background_work(db):
    with (
        mock.patch("plane.db.mixins.soft_delete_related_objects.delay"),
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch("plane.app.views.project.member.project_add_user_email"),
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Groups", identifier="PGR", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


def _person(workspace, email, role=MEMBER):
    user = User.objects.create(email=email, username=email, first_name=email.split("@")[0])
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _as(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _group(workspace, name, parent=None):
    return UserGroup.objects.create(workspace=workspace, name=name, parent=parent)


def _join(group, user):
    return UserGroupMember.objects.create(workspace=group.workspace, group=group, user=user)


def _row(project, user):
    return ProjectMember.objects.get(project=project, member=user)


def _groups_url(project, suffix=""):
    return f"/api/workspaces/{SLUG}/projects/{project.id}/groups/{suffix}"


def _member_url(project, row=None):
    base = f"/api/workspaces/{SLUG}/projects/{project.id}/members/"
    return f"{base}{row.id}/" if row else base


def _link(client, project, group, role=MEMBER):
    return client.post(_groups_url(project), {"group": str(group.id), "role": role}, format="json")


@pytest.mark.contract
@pytest.mark.django_db
class TestLinkingGroups:
    def test_linking_a_group_makes_its_people_members_with_the_role_of_the_group(
        self, session_client, workspace, project
    ):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)

        response = _link(session_client, project, sales, GUEST)

        assert response.status_code == 201, response.data
        assert response.data["group_name"] == "Sales"
        assert response.data["group_source"] == "local"
        assert response.data["role"] == GUEST
        assert response.data["member_count"] == 1
        row = _row(project, ada)
        assert (row.is_active, row.via_group, row.role, row.group_role, row.direct_role) == (
            True,
            True,
            GUEST,
            GUEST,
            None,
        )

    def test_the_people_of_subgroups_are_members_too(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        ada = _person(workspace, "ada@example.com")
        _join(poland, ada)

        _link(session_client, project, sales, MEMBER)

        assert _row(project, ada).role == MEMBER
        assert session_client.get(_groups_url(project)).data[0]["member_count"] == 1

    def test_a_group_cannot_be_an_admin_of_a_project(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")

        response = _link(session_client, project, sales, ADMIN)

        assert response.status_code == 400
        assert not ProjectGroup.objects.filter(project=project).exists()

    def test_a_group_of_another_workspace_and_a_duplicate_are_refused(
        self, session_client, workspace, project, create_user
    ):
        other = Workspace.objects.create(name="Other", slug="other", owner=create_user)
        foreign = _group(other, "Foreign")
        sales = _group(workspace, "Sales")

        assert _link(session_client, project, foreign).status_code == 400
        assert _link(session_client, project, sales).status_code == 201
        assert _link(session_client, project, sales).status_code == 409

    def test_the_role_of_a_group_can_change_and_the_group_can_be_removed(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)
        link_id = _link(session_client, project, sales, GUEST).data["id"]

        changed = session_client.patch(_groups_url(project, f"{link_id}/"), {"role": MEMBER}, format="json")
        assert changed.status_code == 200, changed.data
        assert _row(project, ada).role == MEMBER
        refused = session_client.patch(_groups_url(project, f"{link_id}/"), {"role": ADMIN}, format="json")
        assert refused.status_code == 400

        removed = session_client.delete(_groups_url(project, f"{link_id}/"))
        assert removed.status_code == 204
        assert _row(project, ada).is_active is False

    def test_only_project_admins_change_the_groups_of_a_project_but_everyone_in_it_reads_them(self, workspace, project):
        sales = _group(workspace, "Sales")
        member = _person(workspace, "member@example.com")
        ProjectMember.objects.create(project=project, member=member, role=MEMBER, workspace=workspace)
        guest = _person(workspace, "guest@example.com", GUEST)
        ProjectMember.objects.create(project=project, member=guest, role=GUEST, workspace=workspace)

        assert _link(_as(member), project, sales).status_code == 403
        assert _link(_as(guest), project, sales).status_code == 403
        assert _as(member).get(_groups_url(project)).status_code == 200
        assert _as(guest).get(_groups_url(project)).status_code == 200


@pytest.mark.contract
@pytest.mark.django_db
class TestRolesFromGroupsAndPeople:
    def test_a_group_raises_a_direct_role_but_never_lowers_it(self, session_client, workspace, project):
        guests = _group(workspace, "Guests")
        members = _group(workspace, "Members")
        direct_member = _person(workspace, "m@example.com", MEMBER)
        direct_guest = _person(workspace, "g@example.com", MEMBER)
        ProjectMember.objects.create(project=project, member=direct_member, role=MEMBER, workspace=workspace)
        ProjectMember.objects.create(project=project, member=direct_guest, role=GUEST, workspace=workspace)
        _join(guests, direct_member)
        _join(members, direct_guest)

        link_guests = _link(session_client, project, guests, GUEST).data["id"]
        link_members = _link(session_client, project, members, MEMBER).data["id"]

        stays = _row(project, direct_member)
        assert (stays.role, stays.via_group) == (MEMBER, False)
        raised = _row(project, direct_guest)
        assert (raised.role, raised.direct_role, raised.group_role, raised.via_group) == (MEMBER, GUEST, MEMBER, False)

        session_client.delete(_groups_url(project, f"{link_members}/"))
        back = _row(project, direct_guest)
        assert (back.role, back.direct_role, back.group_role, back.is_active) == (GUEST, None, None, True)
        assert link_guests

    def test_a_direct_admin_stays_an_admin(self, session_client, workspace, project, create_user):
        sales = _group(workspace, "Sales")
        _join(sales, create_user)

        _link(session_client, project, sales, GUEST)

        row = _row(project, create_user)
        assert (row.role, row.group_role, row.direct_role) == (ADMIN, GUEST, None)
        # and leaves the group alone
        UserGroupMember.objects.filter(group=sales, user=create_user).delete()
        reconcile_user(workspace.id, create_user.id)
        row = _row(project, create_user)
        assert (row.role, row.group_role, row.is_active) == (ADMIN, None, True)

    def test_a_workspace_guest_gets_no_more_than_guest(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        visitor = _person(workspace, "visitor@example.com", GUEST)
        _join(sales, visitor)

        _link(session_client, project, sales, MEMBER)

        assert _row(project, visitor).role == GUEST

    def test_only_active_workspace_members_get_in(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        gone = _person(workspace, "gone@example.com")
        _join(sales, gone)
        WorkspaceMember.objects.filter(member=gone).update(is_active=False)

        _link(session_client, project, sales)

        assert not ProjectMember.objects.filter(project=project, member=gone).exists()

    def test_leaving_the_group_takes_the_person_out_of_the_project(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)
        _link(session_client, project, sales)
        assert _row(project, ada).is_active

        response = session_client.delete(f"/api/workspaces/{SLUG}/user-groups/{sales.id}/members/{ada.id}/")

        assert response.status_code == 204
        row = _row(project, ada)
        assert (row.is_active, row.via_group, row.group_role) == (False, False, None)

    def test_joining_a_group_brings_the_person_into_its_projects(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _link(session_client, project, sales)
        assert not ProjectMember.objects.filter(project=project, member=ada).exists()

        response = session_client.post(
            f"/api/workspaces/{SLUG}/user-groups/{sales.id}/members/", {"user_id": str(ada.id)}, format="json"
        )

        assert response.status_code == 201, response.data
        assert _row(project, ada).via_group is True

    def test_deleting_a_group_removes_its_links_and_the_memberships_it_gave(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)
        _link(session_client, project, sales)

        response = session_client.delete(f"/api/workspaces/{SLUG}/user-groups/{sales.id}/")

        assert response.status_code == 204
        assert not ProjectGroup.objects.filter(project=project).exists()
        assert _row(project, ada).is_active is False

    def test_moving_a_group_under_another_gives_its_people_the_projects_of_the_new_parent(
        self, session_client, workspace, project
    ):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland")
        ada = _person(workspace, "ada@example.com")
        _join(poland, ada)
        _link(session_client, project, sales)
        assert not ProjectMember.objects.filter(project=project, member=ada).exists()

        response = session_client.patch(
            f"/api/workspaces/{SLUG}/user-groups/{poland.id}/", {"parent": str(sales.id)}, format="json"
        )

        assert response.status_code == 200, response.data
        assert _row(project, ada).via_group is True

    def test_a_new_workspace_role_is_applied_to_what_groups_give(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)
        _link(session_client, project, sales, MEMBER)
        assert _row(project, ada).role == MEMBER

        membership = WorkspaceMember.objects.get(workspace=workspace, member=ada)
        membership.role = GUEST
        membership.save()
        assert _row(project, ada).role == GUEST

        membership = WorkspaceMember.objects.get(workspace=workspace, member=ada)
        membership.is_active = False
        membership.save()
        assert _row(project, ada).is_active is False

    def test_the_sign_in_sync_reconciles(self, session_client, workspace, project):
        from plane.utils.user_group_sync import sync_external_groups
        from plane.db.models import GroupSource

        ada = _person(workspace, "ada@example.com")
        external = UserGroup.objects.create(
            workspace=workspace, name="Entra Sales", source=GroupSource.ENTRA, external_id="e-1"
        )
        _link(session_client, project, external)

        group = mock.Mock(id="e-1")
        group.name = "Entra Sales"
        sync_external_groups(ada, GroupSource.ENTRA, [group])
        assert _row(project, ada).via_group is True

        sync_external_groups(ada, GroupSource.ENTRA, [])
        assert _row(project, ada).is_active is False

    def test_reconciling_twice_changes_nothing(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)
        _link(session_client, project, sales)
        before = ProjectMember.objects.filter(project=project, member=ada).values()[0]

        reconcile_project(project.id)
        reconcile_user(workspace.id, ada.id)

        assert ProjectMember.objects.filter(project=project, member=ada).values()[0] == before


@pytest.mark.contract
@pytest.mark.django_db
class TestMemberEndpointsWithGroups:
    def _via(self, session_client, workspace, project, role=MEMBER):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)
        _link(session_client, project, sales, role)
        return sales, ada

    def test_the_members_list_tells_who_is_there_through_a_group(self, session_client, workspace, project):
        _, ada = self._via(session_client, workspace, project)

        response = session_client.get(_member_url(project))

        by_member = {str(item["member"]): item for item in response.data}
        assert by_member[str(ada.id)]["via_group"] is True
        assert by_member[str(ada.id)]["group_role"] == MEMBER

    def test_a_person_there_through_a_group_cannot_be_removed_by_hand(self, session_client, workspace, project):
        _, ada = self._via(session_client, workspace, project)

        response = session_client.delete(_member_url(project, _row(project, ada)))

        assert response.status_code == 400
        assert "through a group" in response.data["error"]
        assert _row(project, ada).is_active is True

    def test_such_a_person_cannot_leave_either(self, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        _join(sales, ada)
        ProjectGroup.objects.create(project=project, group=sales, role=MEMBER)
        reconcile_project(project.id)

        response = _as(ada).post(f"/api/workspaces/{SLUG}/projects/{project.id}/members/leave/")

        assert response.status_code == 400
        assert _row(project, ada).is_active is True

    def test_removing_the_direct_part_leaves_the_person_in_through_the_group(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        ProjectMember.objects.create(project=project, member=ada, role=ADMIN, workspace=workspace)
        _join(sales, ada)
        _link(session_client, project, sales, GUEST)

        response = session_client.delete(_member_url(project, _row(project, ada)))

        assert response.status_code == 204
        row = _row(project, ada)
        assert (row.is_active, row.via_group, row.role, row.direct_role) == (True, True, GUEST, None)

    def test_a_role_set_by_an_admin_becomes_the_direct_role(self, session_client, workspace, project):
        _, ada = self._via(session_client, workspace, project, MEMBER)
        row = _row(project, ada)

        higher = session_client.patch(_member_url(project, row), {"role": ADMIN}, format="json")
        assert higher.status_code == 200, higher.data
        row = _row(project, ada)
        assert (row.role, row.via_group, row.group_role) == (ADMIN, False, MEMBER)

        lower = session_client.patch(_member_url(project, row), {"role": GUEST}, format="json")
        assert lower.status_code == 200, lower.data
        row = _row(project, ada)
        # the groups still give Member, so that is the effective role; the own role is Guest
        assert (row.role, row.direct_role, row.group_role, row.via_group) == (MEMBER, GUEST, MEMBER, False)
        assert lower.data["role"] == MEMBER

    def test_adding_a_person_by_hand_who_is_there_through_a_group_makes_the_role_direct(
        self, session_client, workspace, project
    ):
        _, ada = self._via(session_client, workspace, project, GUEST)

        response = session_client.post(
            _member_url(project), {"members": [{"member_id": str(ada.id), "role": MEMBER}]}, format="json"
        )

        assert response.status_code == 201, response.data
        row = _row(project, ada)
        assert (row.role, row.via_group, row.group_role, row.direct_role) == (MEMBER, False, GUEST, None)

    def test_the_groups_cannot_write_the_bookkeeping_through_the_serializer(self, session_client, workspace, project):
        member = _person(workspace, "m@example.com")
        row = ProjectMember.objects.create(project=project, member=member, role=MEMBER, workspace=workspace)

        session_client.patch(_member_url(project, row), {"via_group": True, "group_role": MEMBER}, format="json")

        row.refresh_from_db()
        assert (row.via_group, row.group_role) == (False, None)


@pytest.mark.contract
@pytest.mark.django_db
class TestAssigningWorkItemsToProjectGroups:
    def _issue(self, workspace, project):
        return Issue.objects.create(
            name="Shared", project=project, workspace=workspace, state=State.objects.get(project=project)
        )

    def _url(self, workspace, project, issue):
        return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"

    def test_a_group_that_is_not_a_member_of_the_project_is_refused(self, session_client, workspace, project):
        issue = self._issue(workspace, project)
        outside = _group(workspace, "Outside")

        response = session_client.patch(
            self._url(workspace, project, issue), {"group_assignee_ids": [str(outside.id)]}, format="json"
        )

        assert response.status_code == 400
        assert response.data == {"error": "A work item can only be assigned to groups that are members of its project."}

    def test_a_project_group_and_its_subgroups_are_accepted(self, session_client, workspace, project):
        issue = self._issue(workspace, project)
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        _link(session_client, project, sales)

        response = session_client.patch(
            self._url(workspace, project, issue),
            {"group_assignee_ids": [str(sales.id), str(poland.id)]},
            format="json",
        )

        assert response.status_code == 204, getattr(response, "data", None)

    def test_a_group_taken_out_of_the_project_stays_on_the_work_items_it_has(self, session_client, workspace, project):
        issue = self._issue(workspace, project)
        sales = _group(workspace, "Sales")
        other = _group(workspace, "Other")
        link_id = _link(session_client, project, sales).data["id"]
        url = self._url(workspace, project, issue)
        session_client.patch(url, {"group_assignee_ids": [str(sales.id)]}, format="json")
        session_client.delete(_groups_url(project, f"{link_id}/"))

        # unchanged list: fine; adding a group that is not a member: refused
        same = session_client.patch(url, {"group_assignee_ids": [str(sales.id)]}, format="json")
        added = session_client.patch(url, {"group_assignee_ids": [str(sales.id), str(other.id)]}, format="json")

        assert same.status_code == 204, getattr(same, "data", None)
        assert added.status_code == 400

    def test_the_assignable_groups_are_listed_for_every_member_of_the_project(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        _group(workspace, "Outside")
        _link(session_client, project, sales)
        guest = _person(workspace, "guest@example.com", GUEST)
        ProjectMember.objects.create(project=project, member=guest, role=GUEST, workspace=workspace)

        response = _as(guest).get(_groups_url(project) + "?assignable=1")

        assert response.status_code == 200
        assert sorted(item["name"] for item in response.data) == ["Poland", "Sales"]
        by_name = {item["name"]: item for item in response.data}
        assert by_name["Poland"] == {
            "id": poland.id,
            "name": "Poland",
            "source": "local",
            "parent_id": sales.id,
        }
