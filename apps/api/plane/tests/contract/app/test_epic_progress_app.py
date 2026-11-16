# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Epics are left out of the progress numbers of modules and cycles, and stay in their lists.

An Epic next to its children would count the same work twice. A work item without a type counts.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import (
    Cycle,
    CycleIssue,
    Issue,
    IssueAssignee,
    IssueType,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    State,
)

APP_MODULES = "/api/workspaces/{slug}/projects/{project_id}/modules/"
APP_CYCLES = "/api/workspaces/{slug}/projects/{project_id}/cycles/"
APP_CYCLE_PROGRESS = "/api/workspaces/{slug}/projects/{project_id}/cycles/{cycle_id}/progress/"
APP_MODULE_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/modules/{module_id}/issues/"
WS_MODULES = "/api/workspaces/{slug}/modules/"
WS_CYCLES = "/api/workspaces/{slug}/cycles/"
APP_ARCHIVED_MODULES = "/api/workspaces/{slug}/projects/{project_id}/archived-modules/"
APP_ARCHIVED_CYCLES = "/api/workspaces/{slug}/projects/{project_id}/archived-cycles/"
APP_CYCLE_ANALYTICS = "/api/workspaces/{slug}/projects/{project_id}/cycles/{cycle_id}/analytics/"
API_MODULES = "/api/v1/workspaces/{slug}/projects/{project_id}/modules/"
API_CYCLES = "/api/v1/workspaces/{slug}/projects/{project_id}/cycles/"


def _issue(name, project, workspace, author, state, issue_type=None, parent=None):
    issue = Issue(name=name, project=project, workspace=workspace, state=state, type=issue_type, parent=parent)
    issue.save(created_by_id=author.id)
    return issue


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Prog", identifier="PR", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def states(db, project):
    return {
        group: State.objects.create(name=group, project=project, group=group, default=(group == "backlog"))
        for group in ("backlog", "unstarted", "started", "completed", "cancelled")
    }


@pytest.fixture
def epic_type(db, workspace):
    return IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)


@pytest.fixture
def task_type(db, workspace):
    return IssueType.objects.create(workspace=workspace, name="Task")


@pytest.fixture
def module(db, workspace, project):
    return Module.objects.create(name="Backend", project=project, workspace=workspace)


@pytest.fixture
def cycle(db, workspace, project, create_user):
    now = timezone.now()
    return Cycle.objects.create(
        name="Sprint",
        project=project,
        workspace=workspace,
        owned_by=create_user,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=6),
    )


@pytest.fixture
def board(db, workspace, project, create_user, states, epic_type, task_type, module, cycle):
    """An Epic with two children (one done), a typed task, and an untyped one, all in the module and the cycle."""
    epic = _issue("Epic", project, workspace, create_user, states["started"], epic_type)
    done_child = _issue("Done child", project, workspace, create_user, states["completed"], task_type, parent=epic)
    open_child = _issue("Open child", project, workspace, create_user, states["started"], task_type, parent=epic)
    untyped = _issue("Untyped", project, workspace, create_user, states["completed"])
    items = {"epic": epic, "done": done_child, "open": open_child, "untyped": untyped}
    for issue in items.values():
        ModuleIssue.objects.create(module=module, issue=issue, project=project, workspace=workspace)
        CycleIssue.objects.create(cycle=cycle, issue=issue, project=project, workspace=workspace)
    return items


def _row(response, name):
    rows = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
    return next(row for row in rows if row["name"] == name)


@pytest.mark.contract
class TestModuleNumbers:
    @pytest.mark.django_db
    def test_the_epic_does_not_count_in_the_module(self, session_client, workspace, project, module, board):
        response = session_client.get(APP_MODULES.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK
        row = _row(response, "Backend")
        # done child, open child, untyped: 3 of them, 2 completed. The Epic would have made it 4.
        assert row["total_issues"] == 3
        assert row["completed_issues"] == 2
        assert row["started_issues"] == 1

    @pytest.mark.django_db
    def test_the_epic_is_still_listed_in_the_module(self, session_client, workspace, project, module, board):
        response = session_client.get(
            APP_MODULE_ISSUES.format(slug=workspace.slug, project_id=project.id, module_id=module.id)
        )
        assert response.status_code == status.HTTP_200_OK
        text = str(response.data)
        assert str(board["epic"].id) in text

    @pytest.mark.django_db
    def test_the_public_api_agrees(self, api_key_client, workspace, project, module, board):
        response = api_key_client.get(API_MODULES.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK
        row = _row(response, "Backend")
        assert row["total_issues"] == 3
        assert row["completed_issues"] == 2


@pytest.mark.contract
class TestCycleNumbers:
    @pytest.mark.django_db
    def test_the_epic_does_not_count_in_the_cycle(self, session_client, workspace, project, cycle, board):
        response = session_client.get(APP_CYCLES.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK
        row = _row(response, "Sprint")
        assert row["total_issues"] == 3
        assert row["completed_issues"] == 2

    @pytest.mark.django_db
    def test_cycle_progress_leaves_the_epic_out(self, session_client, workspace, project, cycle, board):
        response = session_client.get(
            APP_CYCLE_PROGRESS.format(slug=workspace.slug, project_id=project.id, cycle_id=cycle.id)
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_issues"] == 3
        assert response.data["completed_issues"] == 2
        assert response.data["started_issues"] == 1

    @pytest.mark.django_db
    def test_the_public_api_agrees(self, api_key_client, workspace, project, cycle, board):
        response = api_key_client.get(API_CYCLES.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK
        row = _row(response, "Sprint")
        assert row["total_issues"] == 3
        assert row["completed_issues"] == 2

    @pytest.mark.django_db
    def test_a_cycle_with_only_an_epic_counts_nothing(
        self, session_client, workspace, project, states, epic_type, create_user
    ):
        now = timezone.now()
        lonely = Cycle.objects.create(
            name="Lonely",
            project=project,
            workspace=workspace,
            owned_by=create_user,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=6),
        )
        epic = _issue("Only epic", project, workspace, create_user, states["started"], epic_type)
        CycleIssue.objects.create(cycle=lonely, issue=epic, project=project, workspace=workspace)
        response = session_client.get(APP_CYCLES.format(slug=workspace.slug, project_id=project.id))
        assert _row(response, "Lonely")["total_issues"] == 0


@pytest.mark.contract
class TestOtherPlaces:
    @pytest.mark.django_db
    def test_workspace_module_and_cycle_views(self, session_client, workspace, module, cycle, board):
        modules = session_client.get(WS_MODULES.format(slug=workspace.slug))
        assert modules.status_code == status.HTTP_200_OK
        assert _row(modules, "Backend")["total_issues"] == 3
        cycles = session_client.get(WS_CYCLES.format(slug=workspace.slug))
        assert cycles.status_code == status.HTTP_200_OK
        assert _row(cycles, "Sprint")["total_issues"] == 3

    @pytest.mark.django_db
    def test_archived_module_and_cycle_views(self, session_client, workspace, project, module, cycle, board):
        Module.objects.filter(pk=module.pk).update(archived_at=timezone.now())
        Cycle.objects.filter(pk=cycle.pk).update(archived_at=timezone.now())
        modules = session_client.get(APP_ARCHIVED_MODULES.format(slug=workspace.slug, project_id=project.id))
        assert modules.status_code == status.HTTP_200_OK
        assert _row(modules, "Backend")["total_issues"] == 3
        cycles = session_client.get(APP_ARCHIVED_CYCLES.format(slug=workspace.slug, project_id=project.id))
        assert cycles.status_code == status.HTTP_200_OK
        assert _row(cycles, "Sprint")["total_issues"] == 3

    @pytest.mark.django_db
    def test_cycle_analytics_distribution_leaves_the_epic_out(
        self, session_client, workspace, project, cycle, board, create_user
    ):
        for key in ("epic", "done"):
            IssueAssignee.objects.create(issue=board[key], assignee=create_user, project=project, workspace=workspace)
        response = session_client.get(
            APP_CYCLE_ANALYTICS.format(slug=workspace.slug, project_id=project.id, cycle_id=cycle.id) + "?type=issues"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        mine = [row for row in response.data["assignees"] if row["assignee_id"] == create_user.id]
        # the done child only; the Epic assigned to the same person is not a second work item of theirs
        assert mine and mine[0]["total_issues"] == 1
