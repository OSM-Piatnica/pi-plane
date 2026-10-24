# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The notification emails are written in the language of their recipient."""

import re
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.template.loader import render_to_string

from plane.bgtasks.email_digest_task import send_email_digest
from plane.db.models import EmailNotificationLog, Profile
from plane.tests.factories import UserFactory
from plane.utils.email_i18n import user_language

CONFIG = ("localhost", "", "", "25", "0", "0", "noreply@example.com")


def _visible_text(html):
    """The mail without its HTML comments, which keep the developers' notes (in English)."""
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def _user(language):
    user = UserFactory()
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.language = language
    profile.save()
    return user


@pytest.mark.unit
@pytest.mark.django_db
class TestUserLanguage:
    def test_is_the_language_of_the_profile(self):
        assert user_language(_user("pl")) == "pl"
        assert user_language(_user("pl-x-podlaski")) == "pl"
        assert user_language(_user("ka-ge")) == "ka-ge"

    def test_is_english_for_an_unsupported_language_or_a_user_without_a_profile(self):
        assert user_language(_user("xx")) == "en"
        assert user_language(UserFactory.build()) == "en"


def _digest_logs(receiver, issues=2):
    actor = UserFactory()
    ids = []
    for number in range(1, issues + 1):
        issue_id = uuid4()
        for field in ("priority", "comment"):
            log = EmailNotificationLog.objects.create(
                receiver=receiver,
                triggered_by=actor,
                entity_identifier=issue_id,
                entity_name="issue",
                data={
                    "issue": {
                        "id": str(issue_id),
                        "name": f"Issue {number}",
                        "identifier": "PRJ",
                        "sequence_id": number,
                        "project_id": str(uuid4()),
                        "workspace_slug": "ws",
                    },
                    "issue_activity": {"field": field},
                },
            )
            ids.append(log.id)
    return ids


@pytest.mark.unit
@pytest.mark.django_db
class TestDigestLanguage:
    def _send(self, receiver, settings, mailoutbox):
        settings.WEB_URL = "http://localhost:3000"
        ids = _digest_logs(receiver)
        with patch("plane.bgtasks.email_digest_task.get_email_configuration", return_value=CONFIG):
            send_email_digest(receiver_id=str(receiver.id), email_notification_ids=ids)
        assert len(mailoutbox) == 1
        return mailoutbox[0]

    def test_polish_receiver_gets_a_polish_digest(self, settings, mailoutbox):
        mail = self._send(_user("pl"), settings, mailoutbox)
        assert mail.subject == "Podsumowanie: 4 aktualizacje w 2 zadaniach"
        html = mail.alternatives[0][0]
        assert "Podsumowanie aktualizacji" in html
        assert "komentarze: 1" in html

    def test_english_receiver_gets_an_english_digest(self, settings, mailoutbox):
        mail = self._send(_user("en"), settings, mailoutbox)
        assert mail.subject == "Digest: 4 updates in 2 work items"
        html = mail.alternatives[0][0]
        assert "Update digest" in html
        assert "comments: 1" in html
        assert "aktualizacj" not in _visible_text(html)

    def test_japanese_receiver_gets_the_full_stop_and_word_order_of_japanese(self, settings, mailoutbox):
        mail = self._send(_user("ja"), settings, mailoutbox)
        assert mail.subject == "まとめ: 作業項目 2 件に 4 件の更新"


@pytest.mark.unit
class TestTemplates:
    def _issue_updates_context(self, language, **overrides):
        context = {
            "email_language": language,
            "lead_actor": "Ann Lee",
            "actors_involved": 1,
            "data": [
                {
                    "actor_detail": {"avatar_url": "", "first_name": "Ann", "last_name": "Lee"},
                    "changes": {
                        "priority": {"old_value": ["low"], "new_value": ["urgent"]},
                        "link": {"old_value": ["a", "b", "c"], "new_value": []},
                        "assignees": {"old_value": [], "new_value": ["Bo", "Cy", "Di"]},
                    },
                    "issue_details": {"name": "Fix it", "identifier": "PRJ-1"},
                    "activity_time": "10:00 AM",
                }
            ],
            "comments": [],
            "issue": {"issue_identifier": "PRJ-1", "name": "Fix it", "issue_url": "http://x/i"},
            "receiver": {"email": "r@example.com"},
            "issue_url": "http://x/i",
            "project_url": "http://x/p",
            "workspace": "ws",
            "project": "Proj",
            "user_preference": "http://x/prefs",
            "entity_type": "issue",
        }
        context.update(overrides)
        return context

    def test_issue_updates_in_polish(self):
        html = render_to_string("emails/notifications/issue-updates.html", self._issue_updates_context("pl"))
        assert "Aktualizacje: PRJ-1" in html
        assert "<strong>Ann Lee</strong>" in html
        assert "Priorytet:" in html and "Pilne" in html and "Niski" in html
        assert "Usunięto 3 linki" in html
        assert "+2 więcej" in html
        assert "Zobacz zadanie" in html
        assert "Updates were made" not in _visible_text(html) and "Assignee" not in _visible_text(html)

    def test_issue_updates_in_english_names_the_others(self):
        html = render_to_string(
            "emails/notifications/issue-updates.html", self._issue_updates_context("en", actors_involved=3)
        )
        assert "Updates were made to the work item by <strong>Ann Lee</strong> and others." in html
        assert "3 links were removed" in html
        assert "Urgent" in html

    def test_project_addition_in_german(self):
        html = render_to_string(
            "emails/notifications/project_addition.html",
            {
                "email_language": "de",
                "project_name": "Proj",
                "workspace_name": "WS",
                "email": "r@example.com",
                "inviter_first_name": "Ann",
                "project_url": "http://x/p",
            },
        )
        assert "Zum Projekt" in html
        assert "<strong>Proj</strong>" in html
        assert "r@example.com" in html and "Hinweis:" in html

    def test_due_reminder_in_russian(self):
        html = render_to_string(
            "emails/notifications/work-item-due-reminder.html",
            {
                "email_language": "ru",
                "greeting": "Здравствуйте, Анна! У вас 1 рабочий элемент со сроком на сегодня (2026-10-24).",
                "sections": [],
                "assigned_url": "http://x/assigned",
            },
        )
        assert "Напоминание о рабочих элементах" in html
        assert "Открыть мои рабочие элементы" in html
        assert "Здравствуйте, Анна!" in html
