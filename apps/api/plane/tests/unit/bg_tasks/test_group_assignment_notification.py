# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Work assigned to a group is announced in the inbox: always to the group's admins, to its other members only
when they opted in."""

from unittest.mock import patch

import pytest

from plane.bgtasks.group_assignment_notification_task import (
    GROUP_ASSIGNMENT_ENTITY,
    notify_group_assignment,
    queue_group_assignment_notifications,
)
from plane.db.models import (
    Issue,
    Notification,
    Project,
    ProjectMember,
    State,
    UserGroup,
    UserGroupMember,
    UserNotificationPreference,
    WorkspaceMember,
)
from plane.db.models.user_group import GroupRole
from plane.tests.factories import UserFactory, WorkspaceFactory


@pytest.fixture
def workspace(db):
    return WorkspaceFactory()


@pytest.fixture
def project(workspace):
    return Project.objects.create(name="Plans", identifier="PL", workspace=workspace)


@pytest.fixture
def issue(project, workspace):
    State.objects.create(
        name="Backlog", color="#000000", group="backlog", default=True, project=project, workspace=workspace
    )
    return Issue.objects.create(name="Plan the launch", project=project, workspace=workspace)


@pytest.fixture
def group(workspace):
    return UserGroup.objects.create(workspace=workspace, name="Sales")


def _person(workspace, project, group=None, role=GroupRole.MEMBER, opted_in=False, in_project=True, **kwargs):
    user = UserFactory(**kwargs)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    if in_project:
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=15, is_active=True)
    if group is not None:
        UserGroupMember.objects.create(workspace=workspace, group=group, user=user, role=role)
    if opted_in:
        preference, _ = UserNotificationPreference.objects.get_or_create(user=user, workspace=None, project=None)
        preference.group_assignment = True
        preference.save()
    return user


def _received(user):
    return list(Notification.objects.filter(receiver=user, entity_name=GROUP_ASSIGNMENT_ENTITY))


@pytest.mark.unit
@pytest.mark.django_db
class TestNotifyGroupAssignment:
    def test_admins_are_told_and_members_only_when_they_opted_in(self, workspace, project, issue, group):
        actor = _person(workspace, project)
        admin = _person(workspace, project, group, role=GroupRole.ADMIN)
        opted_in = _person(workspace, project, group, opted_in=True)
        plain = _person(workspace, project, group)

        notify_group_assignment(str(issue.id), [str(group.id)], str(actor.id))

        assert len(_received(admin)) == 1
        assert len(_received(opted_in)) == 1
        assert _received(plain) == []

    def test_the_entry_carries_what_the_web_app_needs(self, workspace, project, issue, group):
        actor = _person(workspace, project, first_name="Rob", last_name="Roy")
        admin = _person(workspace, project, group, role=GroupRole.ADMIN)
        member = _person(workspace, project, group, opted_in=True)

        notify_group_assignment(str(issue.id), [str(group.id)], str(actor.id))

        entry = _received(admin)[0]
        assert entry.entity_identifier == issue.id
        assert entry.triggered_by == actor
        assert entry.project == project
        assert entry.sender == "in_app:group_assignment"
        assert entry.data["issue"]["identifier"] == "PL"
        assert entry.data["issue"]["id"] == str(issue.id)
        assert entry.data["group_assignment"] == {"group": {"id": str(group.id), "name": "Sales"}, "role": "admin"}
        assert _received(member)[0].data["group_assignment"]["role"] == "member"

    def test_the_person_who_assigned_is_not_told(self, workspace, project, issue, group):
        admin = _person(workspace, project, group, role=GroupRole.ADMIN)
        notify_group_assignment(str(issue.id), [str(group.id)], str(admin.id))
        assert _received(admin) == []

    def test_members_of_the_groups_below_count_for_the_opt_in_but_not_as_admins(self, workspace, project, issue, group):
        actor = _person(workspace, project)
        child = UserGroup.objects.create(workspace=workspace, name="Poland", parent=group)
        child_admin = _person(workspace, project, child, role=GroupRole.ADMIN)
        child_member = _person(workspace, project, child, opted_in=True)

        notify_group_assignment(str(issue.id), [str(group.id)], str(actor.id))

        assert _received(child_admin) == []
        assert len(_received(child_member)) == 1

    def test_somebody_in_several_of_the_groups_is_told_once_as_admin(self, workspace, project, issue, group):
        actor = _person(workspace, project)
        support = UserGroup.objects.create(workspace=workspace, name="Support")
        both = _person(workspace, project, group, opted_in=True)
        UserGroupMember.objects.create(workspace=workspace, group=support, user=both, role=GroupRole.ADMIN)

        notify_group_assignment(str(issue.id), [str(group.id), str(support.id)], str(actor.id))

        entries = _received(both)
        assert len(entries) == 1
        assert entries[0].data["group_assignment"]["role"] == "admin"

    def test_people_who_are_not_in_the_project_deactivated_people_and_bots_are_skipped(
        self, workspace, project, issue, group
    ):
        actor = _person(workspace, project)
        outside = _person(workspace, project, group, role=GroupRole.ADMIN, in_project=False)
        inactive = _person(workspace, project, group, role=GroupRole.ADMIN, is_active=False)
        bot = _person(workspace, project, group, role=GroupRole.ADMIN, is_bot=True)

        notify_group_assignment(str(issue.id), [str(group.id)], str(actor.id))

        assert [_received(user) for user in (outside, inactive, bot)] == [[], [], []]

    def test_an_unknown_work_item_is_ignored(self, workspace, project, issue, group):
        issue_id = str(issue.id)
        issue.delete()
        notify_group_assignment(issue_id, [str(group.id)], None)
        assert not Notification.objects.filter(entity_name=GROUP_ASSIGNMENT_ENTITY).exists()


@pytest.mark.unit
class TestQueueGroupAssignmentNotifications:
    def test_only_the_groups_added_now_are_announced(self):
        with patch("plane.bgtasks.group_assignment_notification_task.notify_group_assignment.delay") as delay:
            queue_group_assignment_notifications("issue", {"a", "b"}, ["b", "c"], "actor")
        delay.assert_called_once_with("issue", ["c"], "actor")

    def test_nothing_is_queued_when_no_group_was_added(self):
        with patch("plane.bgtasks.group_assignment_notification_task.notify_group_assignment.delay") as delay:
            queue_group_assignment_notifications("issue", {"a"}, ["a"], "actor")
            queue_group_assignment_notifications("issue", {"a"}, [], "actor")
        delay.assert_not_called()
