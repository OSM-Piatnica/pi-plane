# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project rule: a work item cannot be completed while it has open sub-items, and reopening a finished sub-item
under a completed parent reopens the parent once the person confirms."""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework import status

from plane.bgtasks.issue_automation_task import close_old_issues
from plane.db.models import Issue, IssueActivity, Project, ProjectMember, State

ACTIVITY = "plane.bgtasks.issue_activities_task.issue_activity.delay"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Rule",
        identifier="RL",
        workspace=workspace,
        created_by=create_user,
        is_parent_completion_rule_enabled=True,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def states(db, workspace, project):
    def make(name, group, **extra):
        return State.objects.create(name=name, project=project, workspace=workspace, group=group, **extra)

    return {
        "todo": make("Todo", "unstarted", default=True),
        "doing": make("Doing", "started", sequence=20000),
        "done": make("Done", "completed"),
        "dropped": make("Dropped", "cancelled"),
    }


def work_item(project, state, name="I", parent=None):
    return Issue.objects.create(name=name, workspace=project.workspace, project=project, state=state, parent=parent)


def app_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def api_url(workspace, project, issue):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def patch(client, url, state, **extra):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch(ACTIVITY),
    ):
        return client.patch(url, {"state_id": str(state.id), **extra}, format="json")


@pytest.mark.contract
@pytest.mark.django_db
class TestCompletingAParent:
    def test_refused_while_a_sub_item_is_open(self, session_client, workspace, project, states):
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["todo"], "open child", parent)
        work_item(project, states["done"], "finished child", parent)

        response = patch(session_client, app_url(workspace, project, parent), states["done"])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "1 sub-item is not done" in str(response.data)
        parent.refresh_from_db()
        assert parent.state_id == states["doing"].id

    def test_allowed_once_children_are_done_or_cancelled(self, session_client, workspace, project, states):
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["done"], "done child", parent)
        work_item(project, states["dropped"], "dropped child", parent)

        response = patch(session_client, app_url(workspace, project, parent), states["done"])

        assert response.status_code == status.HTTP_204_NO_CONTENT
        parent.refresh_from_db()
        assert parent.state_id == states["done"].id

    def test_cancelling_a_parent_with_open_children_is_allowed(self, session_client, workspace, project, states):
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["todo"], "open child", parent)

        response = patch(session_client, app_url(workspace, project, parent), states["dropped"])

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_not_enforced_when_the_rule_is_off(self, session_client, workspace, project, states):
        Project.objects.filter(pk=project.pk).update(is_parent_completion_rule_enabled=False)
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["todo"], "open child", parent)

        response = patch(session_client, app_url(workspace, project, parent), states["done"])

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_public_api_enforces_it_too(self, api_key_client, create_user, workspace, project, states):
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["todo"], "open child", parent)

        response = patch(api_key_client, api_url(workspace, project, parent), states["done"])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        parent.refresh_from_db()
        assert parent.state_id == states["doing"].id

    def test_public_api_allows_it_when_children_are_done(self, api_key_client, create_user, workspace, project, states):
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["done"], "done child", parent)

        response = patch(api_key_client, api_url(workspace, project, parent), states["done"])

        assert response.status_code == status.HTTP_200_OK, response.data


@pytest.mark.contract
@pytest.mark.django_db
class TestReopeningAChild:
    def finished_tree(self, project, states):
        grandparent = work_item(project, states["done"], "grandparent")
        parent = work_item(project, states["done"], "parent", grandparent)
        child = work_item(project, states["done"], "child", parent)
        return grandparent, parent, child

    def test_needs_confirmation_and_names_the_parents(self, session_client, workspace, project, states):
        grandparent, parent, child = self.finished_tree(project, states)

        response = patch(session_client, app_url(workspace, project, child), states["doing"])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "parent_reopen_required"
        assert [p["id"] for p in response.data["parents"]] == [str(parent.id), str(grandparent.id)]
        child.refresh_from_db()
        assert child.state_id == states["done"].id

    def test_confirmed_reopens_the_whole_chain(self, session_client, workspace, project, states):
        grandparent, parent, child = self.finished_tree(project, states)

        response = patch(session_client, app_url(workspace, project, child), states["doing"], reopen_parent=True)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        for item in (child, parent, grandparent):
            item.refresh_from_db()
        assert child.state_id == states["doing"].id
        assert parent.state_id == states["doing"].id
        assert grandparent.state_id == states["doing"].id

    def test_parent_goes_back_to_the_state_it_had_before_completion(self, session_client, workspace, project, states):
        review = State.objects.create(
            name="Review", project=project, workspace=workspace, group="started", sequence=30000
        )
        _, parent, child = self.finished_tree(project, states)
        IssueActivity.objects.create(
            issue=parent,
            project=project,
            workspace=workspace,
            field="state",
            verb="updated",
            old_identifier=review.id,
            new_identifier=states["done"].id,
        )

        response = patch(session_client, app_url(workspace, project, child), states["doing"], reopen_parent=True)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        parent.refresh_from_db()
        assert parent.state_id == review.id

    def test_without_history_the_parent_goes_to_the_first_started_state(
        self, session_client, workspace, project, states
    ):
        _, parent, child = self.finished_tree(project, states)

        patch(session_client, app_url(workspace, project, child), states["todo"], reopen_parent=True)

        parent.refresh_from_db()
        assert parent.state_id == states["doing"].id

    def test_a_cancelled_parent_is_left_alone(self, session_client, workspace, project, states):
        parent = work_item(project, states["dropped"], "parent")
        child = work_item(project, states["done"], "child", parent)

        response = patch(session_client, app_url(workspace, project, child), states["doing"])

        assert response.status_code == status.HTTP_204_NO_CONTENT
        parent.refresh_from_db()
        assert parent.state_id == states["dropped"].id

    def test_moving_between_finished_states_needs_no_confirmation(self, session_client, workspace, project, states):
        _, parent, child = self.finished_tree(project, states)

        response = patch(session_client, app_url(workspace, project, child), states["dropped"])

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_public_api_asks_and_then_reopens(self, api_key_client, create_user, workspace, project, states):
        _, parent, child = self.finished_tree(project, states)

        first = patch(api_key_client, api_url(workspace, project, child), states["doing"])
        second = patch(api_key_client, api_url(workspace, project, child), states["doing"], reopen_parent=True)

        assert first.status_code == status.HTTP_400_BAD_REQUEST
        assert first.data["code"] == "parent_reopen_required"
        assert second.status_code == status.HTTP_200_OK, second.data
        parent.refresh_from_db()
        assert parent.state_id == states["doing"].id

    def test_off_when_the_rule_is_off(self, session_client, workspace, project, states):
        Project.objects.filter(pk=project.pk).update(is_parent_completion_rule_enabled=False)
        _, parent, child = self.finished_tree(project, states)

        response = patch(session_client, app_url(workspace, project, child), states["doing"])

        assert response.status_code == status.HTTP_204_NO_CONTENT
        parent.refresh_from_db()
        assert parent.state_id == states["done"].id


@pytest.mark.contract
@pytest.mark.django_db
class TestAutoClose:
    def stale(self, *issues):
        Issue.objects.filter(pk__in=[i.pk for i in issues]).update(updated_at=timezone.now() - timedelta(days=90))

    def run(self):
        with mock.patch("plane.bgtasks.issue_automation_task.issue_activity.delay"):
            close_old_issues()

    def test_parent_with_open_children_waits_when_closing_would_complete_it(self, project, states):
        Project.objects.filter(pk=project.pk).update(close_in=1, default_state=states["done"])
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["doing"], "child", parent)
        self.stale(parent)  # the child was touched recently, the parent was not

        self.run()

        parent.refresh_from_db()
        assert parent.state_id == states["doing"].id

    def test_parent_is_closed_once_children_are_finished(self, project, states):
        Project.objects.filter(pk=project.pk).update(close_in=1, default_state=states["done"])
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["done"], "child", parent)
        self.stale(parent)

        self.run()

        parent.refresh_from_db()
        assert parent.state_id == states["done"].id

    def test_cancelling_is_not_held_back(self, project, states):
        Project.objects.filter(pk=project.pk).update(close_in=1, default_state=states["dropped"])
        parent = work_item(project, states["doing"], "parent")
        work_item(project, states["doing"], "child", parent)
        self.stale(parent)

        self.run()

        parent.refresh_from_db()
        assert parent.state_id == states["dropped"].id

    def test_without_a_close_state_it_uses_this_projects_cancelled_state(self, workspace, create_user, project, states):
        other = Project.objects.create(name="Other", identifier="OT", workspace=workspace, created_by=create_user)
        State.objects.create(name="Elsewhere", project=other, workspace=workspace, group="cancelled")
        Project.objects.filter(pk=project.pk).update(close_in=1)
        item = work_item(project, states["doing"], "stale")
        self.stale(item)

        self.run()

        item.refresh_from_db()
        assert item.state_id == states["dropped"].id
