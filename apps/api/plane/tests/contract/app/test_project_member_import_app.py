# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Importing the members of a project from CSV rows: people rows, group rows and what is reported as skipped."""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Project,
    ProjectGroup,
    ProjectMember,
    User,
    UserGroup,
    UserGroupMember,
    WorkspaceMember,
)

ADMIN, MEMBER, GUEST = 20, 15, 5
SLUG = "test-workspace"


@pytest.fixture(autouse=True)
def _no_background_work(db):
    with (
        mock.patch("plane.db.mixins.soft_delete_related_objects.delay"),
        mock.patch("plane.app.views.project.member_import.project_add_user_email"),
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Import", identifier="PIM", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    return project


def _person(workspace, email, role=MEMBER):
    user = User.objects.create(email=email, username=email, first_name=email.split("@")[0])
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _group(workspace, name, parent=None):
    return UserGroup.objects.create(workspace=workspace, name=name, parent=parent)


def _url(project):
    return f"/api/workspaces/{SLUG}/projects/{project.id}/members/import/"


def _import(client, project, rows):
    return client.post(_url(project), {"rows": rows}, format="json")


@pytest.mark.contract
@pytest.mark.django_db
class TestImportingPeople:
    def test_people_are_added_with_their_role_and_counted(self, session_client, workspace, project):
        ada = _person(workspace, "ada@example.com")
        bob = _person(workspace, "bob@example.com")

        response = _import(
            session_client,
            project,
            [{"email": "Ada@Example.com", "role": "15"}, {"email": "bob@example.com", "role": 5}],
        )

        assert response.status_code == 200, response.data
        assert response.data["people"] == {"added": 2, "reactivated": 0, "already_members": 0, "skipped": 0}
        assert ProjectMember.objects.get(project=project, member=ada).role == MEMBER
        assert ProjectMember.objects.get(project=project, member=bob).role == GUEST

    def test_existing_removed_and_unknown_people(self, session_client, workspace, project):
        ada = _person(workspace, "ada@example.com")
        bob = _person(workspace, "bob@example.com")
        ProjectMember.objects.create(project=project, member=ada, role=MEMBER, is_active=True)
        ProjectMember.objects.create(project=project, member=bob, role=MEMBER, is_active=False)

        response = _import(
            session_client,
            project,
            [
                {"email": "ada@example.com", "role": 5},
                {"email": "bob@example.com", "role": 5},
                {"email": "nobody@example.com", "role": 15},
                {"email": "ada@example.com", "role": 7},
            ],
        )

        assert response.data["people"] == {"added": 0, "reactivated": 1, "already_members": 1, "skipped": 2}
        # Somebody who already is a member keeps their role
        assert ProjectMember.objects.get(project=project, member=ada).role == MEMBER
        bob_row = ProjectMember.objects.get(project=project, member=bob)
        assert (bob_row.is_active, bob_row.role) == (True, GUEST)
        assert [item["code"] for item in response.data["skipped"]] == ["not_workspace_member", "invalid_role"]

    def test_the_role_cannot_go_against_the_workspace_role(self, session_client, workspace, project):
        _person(workspace, "owner@example.com", ADMIN)
        _person(workspace, "guest@example.com", GUEST)

        response = _import(
            session_client,
            project,
            [{"email": "owner@example.com", "role": 15}, {"email": "guest@example.com", "role": 20}],
        )

        assert [item["code"] for item in response.data["skipped"]] == [
            "role_below_workspace_role",
            "role_above_workspace_role",
        ]
        assert response.data["people"]["added"] == 0

    def test_a_person_who_is_in_only_through_a_group_becomes_a_direct_member(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        ada = _person(workspace, "ada@example.com")
        UserGroupMember.objects.create(workspace=workspace, group=sales, user=ada)
        assert _import(session_client, project, [{"group": "Sales", "role": GUEST}]).status_code == 200
        assert ProjectMember.objects.get(project=project, member=ada).via_group

        response = _import(session_client, project, [{"email": "ada@example.com", "role": MEMBER}])

        assert response.data["people"]["added"] == 1
        row = ProjectMember.objects.get(project=project, member=ada)
        assert (row.via_group, row.role, row.direct_role) == (False, MEMBER, None)
        assert row.group_role == GUEST


@pytest.mark.contract
@pytest.mark.django_db
class TestImportingGroups:
    def test_a_group_row_links_the_group_and_brings_its_people_in(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        ada = _person(workspace, "ada@example.com")
        UserGroupMember.objects.create(workspace=workspace, group=poland, user=ada)

        response = _import(session_client, project, [{"group": "sales", "role": "15"}])

        assert response.data["groups"] == {"added": 1, "updated": 0, "skipped": 0}
        assert ProjectGroup.objects.get(project=project, group=sales).role == MEMBER
        row = ProjectMember.objects.get(project=project, member=ada)
        assert (row.via_group, row.role) == (True, MEMBER)

    def test_a_nested_group_can_be_written_as_a_path(self, session_client, workspace, project):
        sales = _group(workspace, "Sales")
        poland = _group(workspace, "Poland", parent=sales)
        _group(workspace, "Poland")

        response = _import(
            session_client,
            project,
            [{"group": " sales/ POLAND ", "role": GUEST}, {"group": "Poland", "role": GUEST}],
        )

        assert ProjectGroup.objects.filter(project=project, group=poland, role=GUEST).exists()
        # "Poland" is also a top-level group, which is the one a plain name means
        assert ProjectGroup.objects.filter(project=project).count() == 2
        assert response.data["groups"]["added"] == 2

    def test_group_names_with_a_slash_or_a_backslash_are_read_from_their_written_paths(
        self, session_client, workspace, project
    ):
        from plane.utils.group_paths import group_paths

        top = _group(workspace, "R&D/QA")
        other = _group(workspace, "A \\ B")
        nested = _group(workspace, "Team/1", parent=other)
        written = group_paths(workspace.id)

        response = _import(
            session_client,
            project,
            [
                {"group": written[top.id], "role": MEMBER},
                {"group": written[other.id], "role": MEMBER},
                {"group": written[nested.id], "role": GUEST},
            ],
        )

        assert response.data["groups"]["added"] == 3, response.data
        assert set(ProjectGroup.objects.filter(project=project).values_list("group_id", flat=True)) == {
            top.id,
            other.id,
            nested.id,
        }

    def test_a_top_level_group_with_a_slash_is_also_found_by_its_plain_name(self, session_client, workspace, project):
        top = _group(workspace, "R&D/QA")

        _import(session_client, project, [{"group": "R&D/QA", "role": MEMBER}])

        assert ProjectGroup.objects.filter(project=project, group=top).exists()

    def test_a_plain_name_shared_by_two_nested_groups_is_ambiguous(self, session_client, workspace, project):
        _group(workspace, "Team", parent=_group(workspace, "Sales"))
        _group(workspace, "Team", parent=_group(workspace, "Support"))

        response = _import(session_client, project, [{"group": "Team", "role": MEMBER}])

        assert [item["code"] for item in response.data["skipped"]] == ["ambiguous_group"]
        assert not ProjectGroup.objects.filter(project=project).exists()

    def test_an_existing_link_changes_its_role_or_is_reported_as_already_linked(
        self, session_client, workspace, project
    ):
        sales = _group(workspace, "Sales")
        support = _group(workspace, "Support")
        ProjectGroup.objects.create(project=project, workspace=workspace, group=sales, role=MEMBER)
        ProjectGroup.objects.create(project=project, workspace=workspace, group=support, role=GUEST)

        response = _import(
            session_client, project, [{"group": "Sales", "role": GUEST}, {"group": "Support", "role": GUEST}]
        )

        assert response.data["groups"] == {"added": 0, "updated": 1, "skipped": 1}
        assert ProjectGroup.objects.get(project=project, group=sales).role == GUEST
        assert [(item["type"], item["code"]) for item in response.data["skipped"]] == [
            ("group", "group_already_linked")
        ]

    def test_unknown_groups_admin_roles_and_mixed_rows_are_skipped_and_nothing_is_created(
        self, session_client, workspace, project
    ):
        sales = _group(workspace, "Sales")
        _person(workspace, "ada@example.com")

        response = _import(
            session_client,
            project,
            [
                {"group": "Nope", "role": MEMBER},
                {"group": "Sales", "role": ADMIN},
                {"group": "Sales", "email": "ada@example.com", "role": MEMBER},
                {"role": MEMBER},
                {"group": "Sales", "role": "x"},
            ],
        )

        assert [item["code"] for item in response.data["skipped"]] == [
            "unknown_group",
            "group_admin_role",
            "both_email_and_group",
            "missing_value",
            "invalid_role",
        ]
        assert [item["row"] for item in response.data["skipped"]] == [1, 2, 3, 4, 5]
        assert UserGroup.objects.filter(workspace=workspace).count() == 1
        assert not ProjectGroup.objects.filter(project=project, group=sales).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestWhoMayImport:
    def test_only_project_admins_may_import(self, workspace, project):
        member = _person(workspace, "member@example.com")
        ProjectMember.objects.create(project=project, member=member, role=MEMBER, is_active=True)
        _group(workspace, "Sales")

        response = _import(_client(member), project, [{"group": "Sales", "role": MEMBER}])

        assert response.status_code == 403
        assert not ProjectGroup.objects.filter(project=project).exists()

    def test_the_rows_must_be_a_list_of_objects(self, session_client, project):
        assert session_client.post(_url(project), {"rows": []}, format="json").status_code == 400
        assert session_client.post(_url(project), {"rows": ["a@b.c"]}, format="json").status_code == 400
        assert session_client.post(_url(project), {}, format="json").status_code == 400
