# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A person is told, in the inbox, that they were added to a group or that their role in it changed."""

import pytest

from plane.bgtasks.group_membership_notification_task import (
    ADDED,
    GROUP_MEMBERSHIP_ENTITY,
    ROLE_CHANGED,
    notify_group_membership,
)
from plane.db.models import Notification, UserGroup, WorkspaceMember
from plane.db.models.user_group import GroupRole
from plane.tests.factories import UserFactory, WorkspaceFactory


@pytest.fixture
def workspace(db):
    return WorkspaceFactory()


@pytest.fixture
def group(workspace):
    return UserGroup.objects.create(workspace=workspace, name="Sales")


def _person(workspace, **kwargs):
    user = UserFactory(**kwargs)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _received(user):
    return list(Notification.objects.filter(receiver=user, entity_name=GROUP_MEMBERSHIP_ENTITY))


@pytest.mark.unit
@pytest.mark.django_db
class TestNotifyGroupMembership:
    def test_a_person_who_was_added_is_told_with_what_the_web_app_needs(self, workspace, group):
        actor = _person(workspace, first_name="Rob", last_name="Roy")
        person = _person(workspace)

        notify_group_membership(str(group.id), str(person.id), str(actor.id), ADDED, GroupRole.MEMBER)

        (entry,) = _received(person)
        assert entry.workspace == workspace
        assert entry.entity_identifier == group.id
        assert entry.triggered_by == actor
        assert entry.project is None
        assert entry.sender == "in_app:group_membership"
        assert entry.data["group_membership"] == {
            "group": {"id": str(group.id), "name": "Sales"},
            "event": "added",
            "role": "member",
        }

    def test_the_role_is_the_one_the_person_has_now(self, workspace, group):
        actor, person = _person(workspace), _person(workspace)

        notify_group_membership(str(group.id), str(person.id), str(actor.id), ROLE_CHANGED, GroupRole.ADMIN)

        assert _received(person)[0].data["group_membership"]["event"] == "role_changed"
        assert _received(person)[0].data["group_membership"]["role"] == "admin"

    def test_adding_yourself_tells_nobody(self, workspace, group):
        person = _person(workspace)
        notify_group_membership(str(group.id), str(person.id), str(person.id), ADDED, GroupRole.MEMBER)
        assert _received(person) == []

    def test_deactivated_people_and_bots_are_not_told(self, workspace, group):
        actor = _person(workspace)
        inactive, bot = _person(workspace, is_active=False), _person(workspace, is_bot=True)

        for user in (inactive, bot):
            notify_group_membership(str(group.id), str(user.id), str(actor.id), ADDED, GroupRole.MEMBER)

        assert [_received(user) for user in (inactive, bot)] == [[], []]

    def test_an_unknown_group_is_ignored(self, workspace, group):
        person = _person(workspace)
        group_id = str(group.id)
        group.delete(soft=False)
        notify_group_membership(group_id, str(person.id), None, ADDED, GroupRole.MEMBER)
        assert _received(person) == []
