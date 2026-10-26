# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Someone who is assigned only to a sub-item hears about that sub-item, never about its parent."""

import json
from unittest import mock

import pytest

from plane.bgtasks.issue_activities_task import issue_activity
from plane.bgtasks.notification_task import notifications
from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueSubscriber,
    Notification,
    Project,
    ProjectMember,
    State,
    WorkspaceMember,
)
from plane.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _run_the_notification_task_in_line(db):
    """issue_activity hands the notifications to a Celery task; run it where the test can see the result."""
    with mock.patch(
        "plane.bgtasks.issue_activities_task.notifications.delay", side_effect=lambda **kw: notifications(**kw)
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Sub", identifier="SUB", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def states(db, workspace, project):
    return {
        "todo": State.objects.create(name="Todo", project=project, workspace=workspace, group="unstarted", default=True),
        "done": State.objects.create(name="Done", project=project, workspace=workspace, group="completed"),
    }


def member(workspace, project):
    user = UserFactory()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    ProjectMember.objects.create(project=project, member=user, role=15, workspace=workspace, is_active=True)
    return user


def activity(type, issue, actor, requested, current=None, **extra):
    issue_activity(
        type=type,
        requested_data=json.dumps(requested),
        current_instance=json.dumps(current) if current is not None else None,
        issue_id=str(issue.id),
        actor_id=str(actor.id),
        project_id=str(issue.project_id),
        epoch=1,
        notification=True,
        **extra,
    )


def work_item(project, creator, name, assignee=None, parent=None, state=None):
    issue = Issue.objects.create(name=name, workspace=project.workspace, project=project, parent=parent, state=state)
    Issue.objects.filter(pk=issue.pk).update(created_by=creator)
    issue.refresh_from_db()
    if assignee:
        IssueAssignee.objects.create(issue=issue, assignee=assignee, project=project, workspace=project.workspace)
    requested = {"name": name, "assignee_ids": [str(assignee.id)] if assignee else []}
    activity("issue.activity.created", issue, creator, requested)
    return issue


@pytest.mark.unit
@pytest.mark.django_db
class TestSubItemAssignee:
    @pytest.fixture
    def tree(self, workspace, project, create_user, states):
        parent_owner = member(workspace, project)
        sub_owner = member(workspace, project)
        parent = work_item(project, create_user, "Parent", assignee=parent_owner, state=states["todo"])
        sub = work_item(project, create_user, "Sub", assignee=sub_owner, parent=parent, state=states["todo"])
        return {"parent": parent, "sub": sub, "parent_owner": parent_owner, "sub_owner": sub_owner}

    def test_completing_the_sub_item_does_not_make_the_person_a_subscriber_of_the_parent(self, tree, states):
        activity(
            "issue.activity.updated",
            tree["sub"],
            tree["sub_owner"],
            {"state_id": str(states["done"].id)},
            {"state_id": str(states["todo"].id)},
        )

        assert not IssueSubscriber.objects.filter(issue=tree["parent"], subscriber=tree["sub_owner"]).exists()

    def test_changes_to_the_parent_do_not_reach_the_sub_item_assignee(self, tree, states):
        activity(
            "issue.activity.updated",
            tree["sub"],
            tree["sub_owner"],
            {"state_id": str(states["done"].id)},
            {"state_id": str(states["todo"].id)},
        )

        # the parent is worked on afterwards, by its own assignee and by somebody else
        activity("issue.activity.updated", tree["parent"], tree["parent_owner"], {"priority": "high"}, {"priority": "none"})
        activity("issue.activity.updated", tree["parent"], tree["parent"].created_by, {"priority": "low"}, {"priority": "high"})

        assert not Notification.objects.filter(receiver=tree["sub_owner"], entity_identifier=tree["parent"].id).exists()

    def test_the_sub_item_assignee_is_told_about_the_sub_item_only(self, tree, workspace, project):
        other = member(workspace, project)
        activity("issue.activity.updated", tree["sub"], other, {"priority": "high"}, {"priority": "none"})

        received = Notification.objects.filter(receiver=tree["sub_owner"])
        assert received.exists()
        assert set(received.values_list("entity_identifier", flat=True)) == {tree["sub"].id}

    def test_attaching_a_sub_item_to_a_parent_subscribes_nobody_to_the_parent(self, workspace, project, create_user, states):
        parent_owner = member(workspace, project)
        sub_owner = member(workspace, project)
        parent = work_item(project, create_user, "Parent", assignee=parent_owner, state=states["todo"])
        sub = work_item(project, create_user, "Sub", assignee=sub_owner, state=states["todo"])

        # what SubIssuesEndpoint.post records, by the person who attaches it
        activity("issue.activity.updated", sub, parent_owner, {"parent": str(parent.id)}, {"parent": str(sub.id)})

        assert set(IssueSubscriber.objects.filter(issue=parent).values_list("subscriber_id", flat=True)) <= {
            parent_owner.id,
            create_user.id,
        }
