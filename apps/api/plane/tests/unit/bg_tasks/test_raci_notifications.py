# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The people of departments with a RACI role hear about the events the workspace's matrix gives their role."""

import json
from unittest import mock

import pytest

from plane.bgtasks.issue_activities_task import issue_activity
from plane.bgtasks.notification_task import notifications
from plane.db.models import (
    EmailNotificationLog,
    GroupKind,
    Issue,
    IssueRaci,
    IssueSubscriber,
    Notification,
    Project,
    ProjectMember,
    RaciNotificationSetting,
    State,
    UserGroup,
    UserGroupMember,
    WorkspaceFeature,
    WorkspaceMember,
)
from plane.tests.factories import UserFactory
from plane.utils.raci_notifications import SENDER, raci_recipient_ids


@pytest.fixture(autouse=True)
def _run_the_notification_task_in_line(db):
    with mock.patch(
        "plane.bgtasks.issue_activities_task.notifications.delay", side_effect=lambda **kw: notifications(**kw)
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    WorkspaceFeature.objects.create(workspace=workspace, key="raci", is_enabled=True)
    project = Project.objects.create(
        name="Raci", identifier="RCN", workspace=workspace, created_by=create_user, is_raci_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def states(workspace, project):
    return {
        "todo": State.objects.create(
            name="Todo", project=project, workspace=workspace, group="unstarted", default=True
        ),
        "doing": State.objects.create(name="Doing", project=project, workspace=workspace, group="started"),
        "done": State.objects.create(name="Done", project=project, workspace=workspace, group="completed"),
    }


def person(workspace, project=None):
    user = UserFactory()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    if project is not None:
        ProjectMember.objects.create(project=project, member=user, role=15, workspace=workspace, is_active=True)
    return user


def department(workspace, code, *people, is_active=True):
    group = UserGroup.objects.create(
        workspace=workspace, name=code, code=code, kind=GroupKind.DEPARTMENT, is_active=is_active
    )
    for user in people:
        UserGroupMember.objects.create(workspace=workspace, group=group, user=user)
    return group


def give(issue, group, role):
    IssueRaci.objects.create(issue=issue, group=group, role=role, project=issue.project, workspace=issue.workspace)


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


def told(user, issue):
    return Notification.objects.filter(receiver=user, entity_identifier=issue.id)


@pytest.mark.unit
@pytest.mark.django_db
class TestRaciNotifications:
    @pytest.fixture
    def setup(self, workspace, project, states, create_user):
        people = {name: person(workspace, project) for name in ("resp", "cons", "appr", "info", "actor")}
        people["outsider"] = person(workspace)  # in the department, not in the project
        groups = {
            "R": department(workspace, "R", people["resp"], people["outsider"]),
            "C": department(workspace, "C", people["cons"]),
            "A": department(workspace, "A", people["appr"]),
            "I": department(workspace, "I", people["info"]),
        }
        issue = Issue.objects.create(name="Box", workspace=workspace, project=project, state=states["todo"])
        for code, role in (("R", "responsible"), ("C", "consulted"), ("A", "approver"), ("I", "informed")):
            give(issue, groups[code], role)
        return {"people": people, "groups": groups, "issue": issue}

    def change_state(self, setup, states, to):
        activity(
            "issue.activity.updated",
            setup["issue"],
            setup["people"]["actor"],
            {"state_id": str(states[to].id)},
            {"state_id": str(states["todo"].id)},
        )

    def test_state_change_reaches_responsible_consulted_and_informed(self, setup, states):
        self.change_state(setup, states, "doing")

        people, issue = setup["people"], setup["issue"]
        for name in ("resp", "cons", "info"):
            assert told(people[name], issue).filter(sender=SENDER).exists(), name
        assert not told(people["appr"], issue).exists()

    def test_completion_reaches_every_role_once(self, setup, states):
        self.change_state(setup, states, "done")

        people, issue = setup["people"], setup["issue"]
        for name in ("resp", "cons", "info", "appr"):
            assert told(people[name], issue).count() == 1, name

    def test_nobody_outside_the_project_and_not_the_actor(self, setup, states):
        self.change_state(setup, states, "done")

        assert not Notification.objects.filter(receiver=setup["people"]["outsider"]).exists()
        assert not told(setup["people"]["actor"], setup["issue"]).exists()

    def test_other_changes_reach_no_department(self, setup):
        activity(
            "issue.activity.updated",
            setup["issue"],
            setup["people"]["actor"],
            {"priority": "high"},
            {"priority": "none"},
        )

        assert not Notification.objects.filter(sender=SENDER).exists()

    def test_a_subscriber_is_told_as_a_subscriber_not_twice(self, setup, states):
        resp, issue = setup["people"]["resp"], setup["issue"]
        IssueSubscriber.objects.create(issue=issue, subscriber=resp, project=issue.project, workspace=issue.workspace)

        self.change_state(setup, states, "doing")

        assert told(resp, issue).count() == 1
        assert told(resp, issue).first().sender != SENDER

    def test_the_workspace_matrix_decides(self, setup, states, workspace):
        RaciNotificationSetting.objects.create(workspace=workspace, matrix={"state_or_due_date": ["approver"]})

        self.change_state(setup, states, "doing")

        assert set(Notification.objects.filter(sender=SENDER).values_list("receiver_id", flat=True)) == {
            setup["people"]["appr"].id
        }

    def test_email_follows_the_preferences(self, setup, states):
        # by default people get an email when a work item is completed, not for any other change of state
        self.change_state(setup, states, "doing")
        assert not EmailNotificationLog.objects.filter(receiver=setup["people"]["cons"]).exists()

        self.change_state(setup, states, "done")
        assert EmailNotificationLog.objects.filter(receiver=setup["people"]["cons"]).exists()

    def test_nothing_while_the_project_has_raci_off(self, setup, states, project):
        Project.objects.filter(pk=project.pk).update(is_raci_enabled=False)

        self.change_state(setup, states, "doing")

        assert not Notification.objects.filter(sender=SENDER).exists()

    def test_a_switched_off_department_tells_nobody(self, setup, states):
        UserGroup.objects.filter(pk=setup["groups"]["C"].pk).update(is_active=False)

        self.change_state(setup, states, "doing")

        assert not told(setup["people"]["cons"], setup["issue"]).exists()

    def test_approval_events_for_acceptance(self, setup):
        issue = Issue.objects.get(pk=setup["issue"].pk)
        people = setup["people"]

        found = raci_recipient_ids(issue, "approval_requested")

        assert found == {people["resp"].id, people["appr"].id}
        assert raci_recipient_ids(issue, "approval_requested", exclude=[people["resp"].id]) == {people["appr"].id}
