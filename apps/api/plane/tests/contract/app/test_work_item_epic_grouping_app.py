# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the grouping tests of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""Grouping the work item list by the nearest Epic."""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    DeployBoard,
    Issue,
    IssueType,
    Project,
    ProjectIssueType,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)
from plane.utils.epic_ancestor import EpicAncestor
from plane.utils.paginator import BasePaginator

LIST_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/"
PUBLIC_URL = "/api/public/anchor/{anchor}/issues/"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Hierarchy", identifier="HIE", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#ff0000", project=project, workspace=workspace, default=True
    )
    return project


@pytest.fixture
def types(db, workspace, project):
    epic = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
    task = IssueType.objects.create(workspace=workspace, name="Task")
    for issue_type in (epic, task):
        ProjectIssueType.objects.create(project=project, issue_type=issue_type, workspace=workspace)
    return {"epic": epic, "task": task}


@pytest.fixture
def hierarchy(db, workspace, project, create_user, types):
    """Epic A > Task A1 > Subtask A1a, Epic A > Task A2, Epic B > Task B1, and a loose Task."""

    def make(name, issue_type, parent=None, author=create_user):
        issue = Issue(name=name, project=project, workspace=workspace, type=issue_type, parent=parent)
        issue.save(created_by_id=author.id)
        return issue

    epic_a = make("Epic A", types["epic"])
    epic_b = make("Epic B", types["epic"])
    task_a1 = make("Task A1", types["task"], epic_a)
    subtask = make("Subtask A1a", types["task"], task_a1)
    task_a2 = make("Task A2", types["task"], epic_a)
    task_b1 = make("Task B1", types["task"], epic_b)
    loose = make("Loose task", types["task"])
    return {
        "epic_a": epic_a,
        "epic_b": epic_b,
        "task_a1": task_a1,
        "subtask": subtask,
        "task_a2": task_a2,
        "task_b1": task_b1,
        "loose": loose,
        "make": make,
        "task_type": types["task"],
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
class TestGroupByEpic:
    @pytest.mark.django_db
    def test_groups_every_descendant_under_its_nearest_epic(self, session_client, workspace, project, hierarchy):
        data = get_grouped(session_client, workspace, project, group_by="epic_id")

        groups = group_names(data["results"])
        epic_a, epic_b = str(hierarchy["epic_a"].id), str(hierarchy["epic_b"].id)
        assert groups[epic_a] == {"Epic A", "Task A1", "Subtask A1a", "Task A2"}
        assert groups[epic_b] == {"Epic B", "Task B1"}
        assert groups["None"] == {"Loose task"}
        assert data["results"][epic_a]["total_results"] == 4
        subtask_row = next(row for row in data["results"][epic_a]["results"] if row["name"] == "Subtask A1a")
        assert subtask_row["epic_id"] == hierarchy["epic_a"].id

    @pytest.mark.django_db
    def test_works_with_more_than_one_epic_type(self, session_client, workspace, project, hierarchy):
        other_epic_type = IssueType.objects.create(workspace=workspace, name="Big rock", is_epic=True)
        ProjectIssueType.objects.create(project=project, issue_type=other_epic_type, workspace=workspace)
        rock = hierarchy["make"]("Rock", other_epic_type)
        under_rock = hierarchy["make"]("Under rock", hierarchy["task_type"], rock)

        data = get_grouped(session_client, workspace, project, group_by="epic_id")

        groups = group_names(data["results"])
        assert groups[str(rock.id)] == {"Rock", "Under rock"}
        assert str(under_rock.id) in {row["id"] and str(row["id"]) for row in data["results"][str(rock.id)]["results"]}

    @pytest.mark.django_db
    def test_sub_groups_by_epic(self, session_client, workspace, project, hierarchy):
        data = get_grouped(session_client, workspace, project, group_by="state_id", sub_group_by="epic_id")

        (state_group,) = [body for body in data["results"].values() if body["total_results"]]
        sub_groups = group_names(state_group["results"])
        assert sub_groups[str(hierarchy["epic_b"].id)] == {"Epic B", "Task B1"}
        assert sub_groups["None"] == {"Loose task"}

    @pytest.mark.django_db
    def test_a_deleted_epic_no_longer_groups_its_tasks(self, session_client, workspace, project, hierarchy):
        hierarchy["epic_b"].delete()

        data = get_grouped(session_client, workspace, project, group_by="epic_id")

        groups = group_names(data["results"])
        assert str(hierarchy["epic_b"].id) not in groups
        assert groups["None"] == {"Loose task", "Task B1"}

    @pytest.mark.django_db
    def test_an_ungrouped_list_does_not_compute_the_epic(self, session_client, workspace, project, hierarchy):
        response = session_client.get(
            LIST_URL.format(slug=workspace.slug, project_id=project.id), {"sub_issue": "true"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert all("epic_id" not in row for row in response.data["results"])


@pytest.mark.contract
class TestEpicFilter:
    """The filter a client sends to load more work items of one Epic group."""

    def names(self, client, workspace, project, **params):
        response = client.get(
            LIST_URL.format(slug=workspace.slug, project_id=project.id), {"sub_issue": "true", **params}
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        return {row["name"] for row in response.data["results"]}

    @pytest.mark.django_db
    def test_epic_filter(self, session_client, workspace, project, hierarchy):
        epic_b = str(hierarchy["epic_b"].id)

        assert self.names(session_client, workspace, project, epic=str(hierarchy["epic_a"].id)) == {
            "Epic A",
            "Task A1",
            "Subtask A1a",
            "Task A2",
        }
        assert self.names(session_client, workspace, project, epic="None") == {"Loose task"}
        assert self.names(session_client, workspace, project, epic=f"None,{epic_b}") == {
            "Loose task",
            "Epic B",
            "Task B1",
        }

    @pytest.mark.django_db
    def test_the_epic_filter_combines_with_a_group_assignee_style_id_filter(
        self, session_client, workspace, project, hierarchy
    ):
        # another filter that narrows by id must not be overwritten by the Epic filter
        names = self.names(
            session_client, workspace, project, epic=str(hierarchy["epic_a"].id), parent=str(hierarchy["epic_a"].id)
        )
        assert names == {"Task A1", "Task A2"}

    @pytest.mark.django_db
    def test_invalid_identifiers_are_ignored(self, session_client, workspace, project, hierarchy):
        everything = self.names(session_client, workspace, project)

        assert self.names(session_client, workspace, project, epic="not-a-uuid") == everything
        assert self.names(session_client, workspace, project, epic="' OR 1=1 --") == everything


@pytest.mark.contract
class TestEpicGroupingBoundaries:
    @pytest.mark.django_db
    def test_the_epic_grouping_requires_the_annotation(self, project, hierarchy):
        queryset = Issue.issue_objects.filter(project=project)

        assert BasePaginator._has_group_field(queryset, "epic_id") is False
        assert BasePaginator._has_group_field(queryset.annotate(epic_id=EpicAncestor()), "epic_id") is True
        assert BasePaginator._has_group_field(queryset, "parent_id") is True

    @pytest.mark.django_db
    def test_a_guest_only_gets_groups_of_work_items_they_can_list(self, workspace, project, hierarchy):
        uid = uuid4().hex[:8]
        guest = User.objects.create(email=f"guest-{uid}@example.test", username=f"guest_{uid}")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5, is_active=True)
        ProjectMember.objects.create(project=project, member=guest, workspace=workspace, role=5, is_active=True)
        own_task = hierarchy["make"]("Guest task", hierarchy["task_type"], hierarchy["epic_a"], guest)
        client = APIClient()
        client.force_authenticate(user=guest)

        data = get_grouped(client, workspace, project, group_by="epic_id")

        assert set(data["results"]) == {str(hierarchy["epic_a"].id), "None"}
        rows = [row for body in data["results"].values() for row in body["results"]]
        assert [row["id"] for row in rows] == [own_task.id]

    @pytest.mark.django_db
    def test_a_public_board_refuses_the_grouping_and_ignores_the_filter(
        self, workspace, project, hierarchy, create_user
    ):
        board = DeployBoard.objects.create(
            entity_name="project", entity_identifier=project.id, project=project, workspace=workspace
        )
        client = APIClient()

        assert client.get(PUBLIC_URL.format(anchor=board.anchor), {"group_by": "epic_id"}).status_code == 400
        assert (
            client.get(
                PUBLIC_URL.format(anchor=board.anchor), {"group_by": "state_id", "sub_group_by": "epic_id"}
            ).status_code
            == 400
        )
        everything = client.get(PUBLIC_URL.format(anchor=board.anchor))
        filtered = client.get(PUBLIC_URL.format(anchor=board.anchor), {"epic": str(hierarchy["epic_a"].id)})
        assert everything.status_code == filtered.status_code == 200
        assert len(filtered.data) == len(everything.data)
