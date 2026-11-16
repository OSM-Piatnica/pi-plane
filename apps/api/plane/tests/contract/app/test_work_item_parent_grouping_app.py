# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the grouping tests of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""Grouping the work item list by parent."""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, Project, ProjectMember, State, User, WorkspaceMember

LIST_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Hierarchy", identifier="HIE", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#ff0000", project=project, workspace=workspace, default=True
    )
    return project


@pytest.fixture
def hierarchy(db, workspace, project, create_user):
    """Parent A > Child A1 > Grandchild, Parent A > Child A2, Parent B > Child B1, and a loose item."""

    def make(name, parent=None, author=create_user):
        issue = Issue(name=name, project=project, workspace=workspace, parent=parent)
        issue.save(created_by_id=author.id)
        return issue

    parent_a = make("Parent A")
    parent_b = make("Parent B")
    child_a1 = make("Child A1", parent_a)
    grandchild = make("Grandchild", child_a1)
    child_a2 = make("Child A2", parent_a)
    child_b1 = make("Child B1", parent_b)
    loose = make("Loose")
    return {
        "parent_a": parent_a,
        "parent_b": parent_b,
        "child_a1": child_a1,
        "grandchild": grandchild,
        "child_a2": child_a2,
        "child_b1": child_b1,
        "loose": loose,
        "make": make,
    }


def group_names(results):
    return {group: {row["name"] for row in body["results"]} for group, body in results.items()}


def get_grouped(client, workspace, project, **params):
    response = client.get(
        LIST_URL.format(slug=workspace.slug, project_id=project.id),
        {"sub_issue": "true", "per_page": 100, **params},
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    return response.data


@pytest.mark.contract
class TestGroupByParent:
    @pytest.mark.django_db
    def test_groups_work_items_under_their_direct_parent(self, session_client, workspace, project, hierarchy):
        data = get_grouped(session_client, workspace, project, group_by="parent_id")

        groups = group_names(data["results"])
        assert groups[str(hierarchy["parent_a"].id)] == {"Child A1", "Child A2"}
        assert groups[str(hierarchy["child_a1"].id)] == {"Grandchild"}
        assert groups[str(hierarchy["parent_b"].id)] == {"Child B1"}
        assert groups["None"] == {"Parent A", "Parent B", "Loose"}
        assert data["results"][str(hierarchy["parent_a"].id)]["total_results"] == 2
        assert all(row["parent_id"] is None for row in data["results"]["None"]["results"])

    @pytest.mark.django_db
    def test_a_project_without_parents_has_only_the_none_group(self, session_client, workspace, project):
        Issue(name="Alone", project=project, workspace=workspace).save()

        data = get_grouped(session_client, workspace, project, group_by="parent_id")

        assert list(data["results"]) == ["None"]

    @pytest.mark.django_db
    def test_sub_groups_by_parent(self, session_client, workspace, project, hierarchy):
        data = get_grouped(session_client, workspace, project, group_by="state_id", sub_group_by="parent_id")

        (state_group,) = [body for body in data["results"].values() if body["total_results"]]
        sub_groups = group_names(state_group["results"])
        assert sub_groups[str(hierarchy["parent_b"].id)] == {"Child B1"}
        assert sub_groups["None"] == {"Parent A", "Parent B", "Loose"}

    @pytest.mark.django_db
    def test_a_deleted_parent_no_longer_makes_a_group(self, session_client, workspace, project, hierarchy):
        hierarchy["child_b1"].delete()

        data = get_grouped(session_client, workspace, project, group_by="parent_id")

        assert str(hierarchy["parent_b"].id) not in group_names(data["results"])


@pytest.mark.contract
class TestParentFilter:
    """The filter a client sends to load more work items of one group."""

    def names(self, client, workspace, project, **params):
        response = client.get(
            LIST_URL.format(slug=workspace.slug, project_id=project.id), {"sub_issue": "true", **params}
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        return {row["name"] for row in response.data["results"]}

    @pytest.mark.django_db
    def test_parent_filter(self, session_client, workspace, project, hierarchy):
        parent_a = str(hierarchy["parent_a"].id)

        assert self.names(session_client, workspace, project, parent=parent_a) == {"Child A1", "Child A2"}
        assert self.names(session_client, workspace, project, parent="None") == {"Parent A", "Parent B", "Loose"}

    @pytest.mark.django_db
    def test_invalid_identifiers_are_ignored(self, session_client, workspace, project, hierarchy):
        everything = self.names(session_client, workspace, project)

        assert self.names(session_client, workspace, project, parent="not-a-uuid") == everything


@pytest.mark.contract
class TestGroupingBoundaries:
    @pytest.mark.django_db
    def test_unknown_group_field_is_still_rejected(self, session_client, workspace, project, hierarchy):
        response = session_client.get(
            LIST_URL.format(slug=workspace.slug, project_id=project.id), {"group_by": "parent__name"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_a_guest_only_gets_groups_of_work_items_they_can_list(self, workspace, project, hierarchy):
        uid = uuid4().hex[:8]
        guest = User.objects.create(email=f"guest-{uid}@example.test", username=f"guest_{uid}")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5, is_active=True)
        ProjectMember.objects.create(project=project, member=guest, workspace=workspace, role=5, is_active=True)
        own = hierarchy["make"]("Guest item", hierarchy["parent_a"], guest)
        client = APIClient()
        client.force_authenticate(user=guest)

        data = get_grouped(client, workspace, project, group_by="parent_id")

        assert set(data["results"]) == {str(hierarchy["parent_a"].id), "None"}
        rows = [row for body in data["results"].values() for row in body["results"]]
        assert [row["id"] for row in rows] == [own.id]
