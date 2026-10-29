# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for email notification preferences: new-user defaults, the
activity -> toggle mapping, and the per-issue email cap.
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone

from plane.bgtasks.email_digest_task import digest_now, send_email_digest, stack_email_digests
from plane.bgtasks.email_notification_task import stack_email_notification
from plane.bgtasks.notification_task import should_send_email
from plane.db.models import EmailNotificationLog, UserNotificationPreference
from plane.tests.factories import UserFactory


def _pref(**overrides):
    values = dict(property_change=False, state_change=False, comment=False, mention=False, issue_completed=False)
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.unit
@pytest.mark.django_db
class TestNewUserDefaults:
    def test_new_user_gets_quiet_defaults(self):
        user = UserFactory()
        pref = UserNotificationPreference.objects.get(user=user)
        assert pref.mention is True
        assert pref.comment is True
        assert pref.issue_completed is True
        assert pref.state_change is False
        assert pref.property_change is False


@pytest.mark.unit
class TestShouldSendEmail:
    def test_property_change_only_follows_property_toggle(self):
        activity = {"field": "priority"}
        assert should_send_email(_pref(property_change=True), activity, uuid4()) is True
        assert should_send_email(_pref(state_change=True, comment=True), activity, uuid4()) is False

    def test_comment_only_follows_comment_toggle(self):
        activity = {"field": "comment"}
        assert should_send_email(_pref(comment=True), activity, uuid4()) is True
        # property_change must not leak into comments
        assert should_send_email(_pref(property_change=True), activity, uuid4()) is False

    def test_state_change_does_not_fall_through_to_property_toggle(self):
        activity = {"field": "state", "new_identifier": str(uuid4())}
        with patch("plane.bgtasks.notification_task.State.objects.filter") as state_filter:
            state_filter.return_value.exists.return_value = False
            assert should_send_email(_pref(state_change=True), activity, uuid4()) is True
            assert should_send_email(_pref(property_change=True), activity, uuid4()) is False

    def test_completed_state_follows_issue_completed_toggle(self):
        activity = {"field": "state", "new_identifier": str(uuid4())}
        with patch("plane.bgtasks.notification_task.State.objects.filter") as state_filter:
            state_filter.return_value.exists.return_value = True
            assert should_send_email(_pref(issue_completed=True), activity, uuid4()) is True
            assert should_send_email(_pref(property_change=True), activity, uuid4()) is False

    def test_non_completed_state_ignores_issue_completed_toggle(self):
        activity = {"field": "state", "new_identifier": str(uuid4())}
        with patch("plane.bgtasks.notification_task.State.objects.filter") as state_filter:
            state_filter.return_value.exists.return_value = False
            assert should_send_email(_pref(issue_completed=True), activity, uuid4()) is False


def _log(receiver, actor, issue_id, field="priority", processed_at=None):
    return EmailNotificationLog.objects.create(
        receiver=receiver,
        triggered_by=actor,
        entity_identifier=issue_id,
        entity_name="issue",
        data={"issue_activity": {"field": field}},
        processed_at=processed_at,
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestPerIssueEmailCap:
    @pytest.fixture(autouse=True)
    def _cap_settings(self, settings):
        settings.EMAIL_NOTIFICATION_MAX_PER_ISSUE = 2
        settings.EMAIL_NOTIFICATION_WINDOW_MINUTES = 60

    def _stack(self):
        with patch("plane.bgtasks.email_notification_task.send_email_notification.delay") as send:
            stack_email_notification()
        return send

    def test_pending_logs_are_sent_and_marked_processed(self):
        receiver, actor, issue_id = UserFactory(), UserFactory(), uuid4()
        log = _log(receiver, actor, issue_id)
        send = self._stack()
        assert send.call_count == 1
        log.refresh_from_db()
        assert log.processed_at is not None

    def test_cap_holds_back_activity_instead_of_dropping_it(self):
        receiver, actor, issue_id = UserFactory(), UserFactory(), uuid4()
        now = timezone.now()
        # two emails already sent within the window
        _log(receiver, actor, issue_id, processed_at=now - timedelta(minutes=10))
        _log(receiver, actor, issue_id, processed_at=now - timedelta(minutes=5))
        pending = _log(receiver, actor, issue_id)

        send = self._stack()
        assert send.call_count == 0
        pending.refresh_from_db()
        assert pending.processed_at is None

    def test_held_back_activity_goes_out_once_window_frees_up(self):
        receiver, actor, issue_id = UserFactory(), UserFactory(), uuid4()
        now = timezone.now()
        _log(receiver, actor, issue_id, processed_at=now - timedelta(minutes=90))
        _log(receiver, actor, issue_id, processed_at=now - timedelta(minutes=80))
        pending = _log(receiver, actor, issue_id)

        send = self._stack()
        assert send.call_count == 1
        pending.refresh_from_db()
        assert pending.processed_at is not None

    def test_mentions_bypass_the_cap(self):
        receiver, actor, issue_id = UserFactory(), UserFactory(), uuid4()
        now = timezone.now()
        _log(receiver, actor, issue_id, processed_at=now - timedelta(minutes=10))
        _log(receiver, actor, issue_id, processed_at=now - timedelta(minutes=5))
        _log(receiver, actor, issue_id, field="mention")

        assert self._stack().call_count == 1

    def test_cap_is_per_issue_and_per_receiver(self):
        receiver, other, actor = UserFactory(), UserFactory(), UserFactory()
        busy_issue, quiet_issue = uuid4(), uuid4()
        now = timezone.now()
        _log(receiver, actor, busy_issue, processed_at=now - timedelta(minutes=10))
        _log(receiver, actor, busy_issue, processed_at=now - timedelta(minutes=5))
        _log(receiver, actor, busy_issue)  # held back
        _log(receiver, actor, quiet_issue)  # other issue, sent
        _log(other, actor, busy_issue)  # other receiver, sent

        assert self._stack().call_count == 2


def _set_frequency(user, frequency):
    UserNotificationPreference.objects.filter(user=user).update(email_frequency=frequency)


@pytest.mark.unit
@pytest.mark.django_db
class TestEmailDigest:
    def test_default_frequency_is_instant(self):
        user = UserFactory()
        assert UserNotificationPreference.objects.get(user=user).email_frequency == "instant"

    def test_instant_stacking_leaves_digest_receivers_alone(self):
        receiver, actor = UserFactory(), UserFactory()
        _set_frequency(receiver, "hourly")
        log = _log(receiver, actor, uuid4())
        with patch("plane.bgtasks.email_notification_task.send_email_notification.delay") as send:
            stack_email_notification()
        assert send.call_count == 0
        log.refresh_from_db()
        assert log.processed_at is None

    def test_mentions_still_go_out_instantly_for_digest_receivers(self):
        receiver, actor = UserFactory(), UserFactory()
        _set_frequency(receiver, "daily")
        _log(receiver, actor, uuid4(), field="mention")
        with patch("plane.bgtasks.email_notification_task.send_email_notification.delay") as send:
            stack_email_notification()
        assert send.call_count == 1

    def _stack_digests(self, **kwargs):
        with patch("plane.bgtasks.email_digest_task.send_email_digest.delay") as send:
            stack_email_digests(**kwargs)
        return send

    def test_hourly_digest_collects_all_pending_logs_of_a_receiver(self):
        receiver, actor = UserFactory(), UserFactory()
        _set_frequency(receiver, "hourly")
        logs = [_log(receiver, actor, uuid4()) for _ in range(3)]
        send = self._stack_digests()
        assert send.call_count == 1
        assert sorted(send.call_args.kwargs["email_notification_ids"]) == sorted(log.id for log in logs)
        for log in logs:
            log.refresh_from_db()
            assert log.processed_at is not None

    def test_instant_receivers_are_not_digested(self):
        receiver, actor = UserFactory(), UserFactory()
        log = _log(receiver, actor, uuid4())
        assert self._stack_digests(force_daily=True).call_count == 0
        log.refresh_from_db()
        assert log.processed_at is None

    def test_daily_digest_only_at_the_configured_hour(self, settings):
        receiver, actor = UserFactory(), UserFactory()
        _set_frequency(receiver, "daily")
        _log(receiver, actor, uuid4())
        now_hour = digest_now().hour
        settings.EMAIL_DIGEST_DAILY_HOUR = (now_hour + 1) % 24
        assert self._stack_digests().call_count == 0
        settings.EMAIL_DIGEST_DAILY_HOUR = now_hour
        assert self._stack_digests().call_count == 1

    def test_send_email_digest_sends_one_email_with_a_row_per_issue(self, settings, mailoutbox):
        settings.WEB_URL = "http://localhost:3000"
        receiver, actor = UserFactory(), UserFactory()
        issue_ids = [uuid4(), uuid4()]
        ids = []
        for number, issue_id in enumerate(issue_ids, start=1):
            for field in ("priority", "comment"):
                log = _log(receiver, actor, issue_id, field=field)
                log.data = {
                    "issue": {
                        "id": str(issue_id),
                        "name": f"Issue {number}",
                        "identifier": "PRJ",
                        "sequence_id": number,
                        "project_id": str(uuid4()),
                        "workspace_slug": "ws",
                    },
                    "issue_activity": {"field": field},
                }
                log.save()
                ids.append(log.id)

        config = ("localhost", "", "", "25", "0", "0", "noreply@example.com")
        with patch("plane.bgtasks.email_digest_task.get_email_configuration", return_value=config):
            send_email_digest(receiver_id=str(receiver.id), email_notification_ids=ids)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [receiver.email]
        html = mailoutbox[0].alternatives[0][0]
        assert "PRJ-1" in html and "PRJ-2" in html
        assert EmailNotificationLog.objects.filter(pk__in=ids, sent_at__isnull=False).count() == 4
