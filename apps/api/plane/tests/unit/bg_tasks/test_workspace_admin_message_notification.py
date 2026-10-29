# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A message to the admins of a workspace: who gets it, what lands in their inbox and what the email looks like."""

from unittest.mock import patch

import pytest

from plane.bgtasks import workspace_admin_message_notification as task_module
from plane.bgtasks.workspace_admin_message_notification import (
    ADMIN_MESSAGE_ENTITY,
    create_admin_message_notifications,
    display_name,
    email_workspace_admin_message,
    wants_admin_message_emails,
    workspace_admin_recipients,
)
from plane.db.models import Notification, Profile, UserNotificationPreference, WorkspaceMember
from plane.tests.factories import UserFactory, WorkspaceFactory

ADMIN, MEMBER, GUEST = 20, 15, 5
CONFIG = ("localhost", "", "", "25", "0", "0", "noreply@example.com")


def _user(workspace, role, language="en", **kwargs):
    user = UserFactory(**kwargs)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.language = language
    profile.save()
    return user


@pytest.fixture
def workspace(db):
    return WorkspaceFactory(name="Acme")


@pytest.mark.unit
@pytest.mark.django_db
class TestRecipients:
    def test_only_the_admins_are_written_to(self, workspace):
        admin, member, guest = _user(workspace, ADMIN), _user(workspace, MEMBER), _user(workspace, GUEST)

        recipients = workspace_admin_recipients(workspace, member.id)

        assert [user.id for user in recipients] == [admin.id]
        assert guest.id not in {user.id for user in recipients}

    def test_an_admin_who_writes_does_not_write_to_themselves(self, workspace):
        writer, other = _user(workspace, ADMIN), _user(workspace, ADMIN)

        assert [user.id for user in workspace_admin_recipients(workspace, writer.id)] == [other.id]

    def test_deactivated_admins_and_bots_are_skipped(self, workspace):
        _user(workspace, ADMIN, is_active=False)
        _user(workspace, ADMIN, is_bot=True)
        writer = _user(workspace, MEMBER)
        membership_inactive = _user(workspace, ADMIN)
        WorkspaceMember.objects.filter(member=membership_inactive).update(is_active=False)

        assert workspace_admin_recipients(workspace, writer.id) == []


@pytest.mark.unit
@pytest.mark.django_db
class TestInboxEntries:
    def test_every_admin_gets_an_entry_with_what_the_web_app_shows(self, workspace):
        first, second = _user(workspace, ADMIN), _user(workspace, ADMIN)
        sender = _user(workspace, MEMBER, first_name="Rob", last_name="Roy", email="rob@example.com")

        message_id, recipients = create_admin_message_notifications(workspace, sender, "Please add me to Sales")

        assert {user.id for user in recipients} == {first.id, second.id}
        entries = Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY, entity_identifier=message_id)
        assert {entry.receiver_id for entry in entries} == {first.id, second.id}
        entry = entries.first()
        assert entry.workspace_id == workspace.id and entry.project_id is None
        assert entry.triggered_by_id == sender.id
        assert entry.message_stripped == "Please add me to Sales"
        assert entry.data["workspace_admin_message"] == {
            "id": str(message_id),
            "message": "Please add me to Sales",
            "sender_email": "rob@example.com",
        }

    def test_nobody_to_write_to_makes_no_entry(self, workspace):
        sender = _user(workspace, MEMBER)

        assert create_admin_message_notifications(workspace, sender, "Hello") == (None, [])
        assert not Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestEmail:
    def _send(self, workspace, sender, message):
        message_id, _ = create_admin_message_notifications(workspace, sender, message)
        with patch("plane.bgtasks.workspace_admin_message_notification.get_email_configuration", return_value=CONFIG):
            email_workspace_admin_message(str(workspace.id), str(message_id))

    def test_each_admin_gets_an_email_that_is_answered_to_the_sender(self, workspace, mailoutbox):
        admin = _user(workspace, ADMIN, email="admin@example.com")
        sender = _user(workspace, GUEST, first_name="Rob", last_name="Roy", email="rob@example.com")

        self._send(workspace, sender, "Please add me to Sales")

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [admin.email]
        assert mail.reply_to == ["rob@example.com"]
        assert mail.subject == f"{display_name(sender)} wrote to the admins of Acme"
        html = mail.alternatives[0][0]
        assert "Please add me to Sales" in html and "rob@example.com" in html

    def test_it_is_written_in_the_language_of_the_admin(self, workspace, mailoutbox):
        _user(workspace, ADMIN, language="de")
        sender = _user(workspace, MEMBER, first_name="Rob", last_name="Roy")

        self._send(workspace, sender, "Hallo")

        assert "Administratoren" in mailoutbox[0].subject

    def test_the_message_cannot_inject_markup_and_keeps_its_line_breaks(self, workspace, mailoutbox):
        _user(workspace, ADMIN)
        sender = _user(workspace, MEMBER)

        self._send(workspace, sender, "<script>alert(1)</script>\nsecond line")

        html = mailoutbox[0].alternatives[0][0]
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;<br>second line" in html

    def test_a_failing_send_does_not_stop_the_other_admins_getting_theirs(self, workspace, mailoutbox):
        _user(workspace, ADMIN, email="first@example.com")
        _user(workspace, ADMIN, email="second@example.com")
        sender = _user(workspace, MEMBER)
        message_id, _ = create_admin_message_notifications(workspace, sender, "Hello")
        real_send = task_module._send_email
        calls = []

        def flaky(receiver, context, subject, reply_to):
            calls.append(receiver.email)
            if len(calls) == 1:
                raise RuntimeError("smtp down")
            return real_send(receiver, context, subject, reply_to)

        with (
            patch("plane.bgtasks.workspace_admin_message_notification.get_email_configuration", return_value=CONFIG),
            patch("plane.bgtasks.workspace_admin_message_notification._send_email", side_effect=flaky),
        ):
            email_workspace_admin_message(str(workspace.id), str(message_id))

        assert len(calls) == 2
        assert len(mailoutbox) == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestOptOut:
    def test_the_emails_are_on_unless_the_admin_turned_them_off(self, workspace):
        admin = _user(workspace, ADMIN)

        assert wants_admin_message_emails(admin) is True
        UserNotificationPreference.objects.create(user=admin, workspace_admin_message=False)
        assert wants_admin_message_emails(admin) is False

    def test_the_default_of_a_new_preference_is_on(self, workspace):
        admin = _user(workspace, ADMIN)

        assert UserNotificationPreference.objects.create(user=admin).workspace_admin_message is True

    def test_an_admin_who_opted_out_gets_no_email_but_keeps_the_inbox_entry_and_the_others_are_mailed(
        self, workspace, mailoutbox
    ):
        quiet = _user(workspace, ADMIN, email="quiet@example.com")
        loud = _user(workspace, ADMIN, email="loud@example.com")
        UserNotificationPreference.objects.create(user=quiet, workspace_admin_message=False)
        sender = _user(workspace, MEMBER)
        message_id, _ = create_admin_message_notifications(workspace, sender, "Hello")

        with patch("plane.bgtasks.workspace_admin_message_notification.get_email_configuration", return_value=CONFIG):
            email_workspace_admin_message(str(workspace.id), str(message_id))

        assert [mail.to for mail in mailoutbox] == [[loud.email]]
        assert Notification.objects.filter(receiver=quiet, entity_identifier=message_id).exists()
