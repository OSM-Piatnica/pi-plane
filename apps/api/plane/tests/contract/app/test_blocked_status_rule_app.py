# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project rule: a work item cannot be started or completed while a work item that blocks it is still open."""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework import status

from plane.bgtasks.issue_automation_task import close_old_issues
from plane.db.models import Issue, IssueRelation, Project, ProjectMember, State

ACTIVITY = "plane.bgtasks.issue_activities_task.issue_activity.delay"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Block", identifier="BLK", workspace=workspace, created_by=create_user, is_blocked_status_rule_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def states(db, workspace, project):
    def make(name, group, **extra):
        return State.objects.create(name=name, project=project, workspace=workspace, group=group, **extra)

    return {
        "backlog": make("Backlog", "backlog"),
        "todo": make("Todo", "unstarted", default=True),
        "doing": make("Doing", "started", sequence=20000),
        "done": make("Done", "completed"),
        "dropped": make("Dropped", "cancelled"),
    }


def work_item(project, state, name="I"):
    return Issue.objects.create(name=name, workspace=project.workspace, project=project, state=state)


def block(project, blocked, blocker):
    """``blocked`` is blocked by ``blocker``."""
    return IssueRelation.objects.create(
        issue=blocked,
        related_issue=blocker,
        relation_type="blocked_by",
        project=project,
        workspace=project.workspace,
    )


def app_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def api_url(workspace, project, issue):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def move(client, url, state, field="state_id"):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch(ACTIVITY),
    ):
        return client.patch(url, {field: str(state.id)}, format="json")


@pytest.mark.contract
@pytest.mark.django_db
class TestBlockedItemStatus:
    @pytest.mark.parametrize("target, verb", [("doing", "started"), ("done", "completed")])
    def test_refused_while_a_blocker_is_open(self, session_client, workspace, project, states, target, verb):
        blocker = work_item(project, states["doing"], "blocker")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, blocker)

        response = move(session_client, app_url(workspace, project, blocked), states[target])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        message = str(response.data)
        assert f"cannot be {verb}" in message
        assert f"BLK-{blocker.sequence_id}" in message
        blocked.refresh_from_db()
        assert blocked.state_id == states["todo"].id

    def test_allowed_once_the_blocker_is_done_or_cancelled(self, session_client, workspace, project, states):
        done_blocker = work_item(project, states["done"], "finished")
        dropped_blocker = work_item(project, states["dropped"], "dropped")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, done_blocker)
        block(project, blocked, dropped_blocker)

        started = move(session_client, app_url(workspace, project, blocked), states["doing"])
        completed = move(session_client, app_url(workspace, project, blocked), states["done"])

        assert started.status_code == status.HTTP_204_NO_CONTENT
        assert completed.status_code == status.HTTP_204_NO_CONTENT

    def test_waiting_or_cancelling_is_always_allowed(self, session_client, workspace, project, states):
        blocker = work_item(project, states["doing"], "blocker")
        blocked = work_item(project, states["doing"], "blocked")
        block(project, blocked, blocker)

        back_to_todo = move(session_client, app_url(workspace, project, blocked), states["todo"])
        backlog = move(session_client, app_url(workspace, project, blocked), states["backlog"])
        cancelled = move(session_client, app_url(workspace, project, blocked), states["dropped"])

        assert back_to_todo.status_code == backlog.status_code == cancelled.status_code == status.HTTP_204_NO_CONTENT

    def test_names_the_first_blockers_and_counts_the_rest(self, session_client, workspace, project, states):
        blocked = work_item(project, states["todo"], "blocked")
        blockers = [work_item(project, states["todo"], f"blocker {n}") for n in range(5)]
        for blocker in blockers:
            block(project, blocked, blocker)

        response = move(session_client, app_url(workspace, project, blocked), states["doing"])

        message = str(response.data)
        assert "blocked by 5 work items that are not done" in message
        assert "and 2 more" in message
        assert f"BLK-{blockers[0].sequence_id}" in message

    def test_a_blocker_in_another_project_counts(self, session_client, workspace, create_user, project, states):
        other = Project.objects.create(name="Other", identifier="OTH", workspace=workspace, created_by=create_user)
        other_state = State.objects.create(
            name="Doing", project=other, workspace=workspace, group="started", default=True
        )
        blocker = work_item(other, other_state, "elsewhere")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, blocker)

        response = move(session_client, app_url(workspace, project, blocked), states["doing"])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert f"OTH-{blocker.sequence_id}" in str(response.data)

    def test_the_blocker_itself_is_free_to_move(self, session_client, workspace, project, states):
        blocker = work_item(project, states["todo"], "blocker")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, blocker)

        response = move(session_client, app_url(workspace, project, blocker), states["doing"])

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_not_enforced_when_the_rule_is_off(self, session_client, workspace, project, states):
        Project.objects.filter(pk=project.pk).update(is_blocked_status_rule_enabled=False)
        blocker = work_item(project, states["doing"], "blocker")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, blocker)

        response = move(session_client, app_url(workspace, project, blocked), states["doing"])

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_public_api_enforces_it_too(self, api_key_client, create_user, workspace, project, states):
        blocker = work_item(project, states["doing"], "blocker")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, blocker)

        refused = move(api_key_client, api_url(workspace, project, blocked), states["doing"], field="state")
        block_done = IssueRelation.objects.get().related_issue
        Issue.objects.filter(pk=block_done.pk).update(state=states["done"])
        allowed = move(api_key_client, api_url(workspace, project, blocked), states["doing"], field="state")

        assert refused.status_code == status.HTTP_400_BAD_REQUEST
        assert allowed.status_code == status.HTTP_200_OK, allowed.data

    def test_a_blocked_item_with_no_open_blocker_is_unaffected_by_the_parent_rule_too(
        self, session_client, workspace, project, states
    ):
        # both rules can be on at once
        Project.objects.filter(pk=project.pk).update(is_parent_completion_rule_enabled=True)
        blocked = work_item(project, states["todo"], "blocked")

        response = move(session_client, app_url(workspace, project, blocked), states["done"])

        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.contract
@pytest.mark.django_db
class TestAutoCloseAndBlockers:
    def run(self):
        with mock.patch("plane.bgtasks.issue_automation_task.issue_activity.delay"):
            close_old_issues()

    def stale(self, *issues):
        Issue.objects.filter(pk__in=[i.pk for i in issues]).update(updated_at=timezone.now() - timedelta(days=90))

    def test_a_blocked_item_is_left_for_the_next_run_when_closing_would_start_or_complete_it(self, project, states):
        Project.objects.filter(pk=project.pk).update(close_in=1, default_state=states["done"])
        blocker = work_item(project, states["doing"], "blocker")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, blocker)
        self.stale(blocked)

        self.run()

        blocked.refresh_from_db()
        assert blocked.state_id == states["todo"].id

    def test_cancelling_is_not_held_back(self, project, states):
        Project.objects.filter(pk=project.pk).update(close_in=1, default_state=states["dropped"])
        blocker = work_item(project, states["doing"], "blocker")
        blocked = work_item(project, states["todo"], "blocked")
        block(project, blocked, blocker)
        self.stale(blocked)

        self.run()

        blocked.refresh_from_db()
        assert blocked.state_id == states["dropped"].id
