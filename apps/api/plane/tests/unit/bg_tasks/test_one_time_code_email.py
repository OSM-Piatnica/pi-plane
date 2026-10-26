# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The sign-in code email is written in the language of the person it goes to."""

from unittest.mock import patch

import pytest

from plane.bgtasks.one_time_code_task import send_one_time_code
from plane.db.models import Profile
from plane.tests.factories import UserFactory
from plane.utils.email_i18n import language_from_accept_header

CONFIG = ("localhost", "", "", "25", "0", "0", "noreply@example.com")


@pytest.mark.unit
class TestLanguageFromAcceptHeader:
    @pytest.mark.parametrize(
        "header, expected",
        [
            ("pl-PL,pl;q=0.9,en;q=0.8", "pl"),
            ("de-AT", "de"),
            ("uk-UA,uk;q=0.9", "ua"),
            ("ka", "ka-ge"),
            ("tr-TR", "tr-TR"),
            ("zh-Hant-TW", "zh-TW"),
            ("zh-CN", "zh-CN"),
            ("zh", "en"),
            ("pt-PT", "pt-PT"),
            ("pt", "pt-BR"),
            ("pl-x-podlaski", "pl"),
            ("xx, fr;q=0.5", "fr"),
            ("en-US,en;q=0.9", "en"),
            ("*", "en"),
            ("", "en"),
            (None, "en"),
        ],
    )
    def test_picks_the_first_language_that_has_emails(self, header, expected):
        assert language_from_accept_header(header) == expected


def _send(email, token="123456", accept_language=None):
    with patch("plane.bgtasks.one_time_code_task.get_email_configuration", return_value=CONFIG):
        send_one_time_code(email, f"one_time_code_{email}", token, accept_language=accept_language)


@pytest.mark.unit
@pytest.mark.django_db
class TestOneTimeCodeEmail:
    def test_english_by_default(self, mailoutbox):
        _send("new@example.com", accept_language=None)

        mail = mailoutbox[0]
        assert mail.subject == "Your one-time Pi-Plane login code is 123456"
        html = mail.alternatives[0][0]
        assert 'lang="en"' in html
        assert "This code is valid for the next 10 minutes" in html

    def test_a_known_user_gets_the_language_of_their_profile(self, mailoutbox):
        user = UserFactory(email="known@example.com")
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.language = "pl"
        profile.save()

        # the browser says German, the profile wins
        _send("known@example.com", accept_language="de")

        mail = mailoutbox[0]
        assert mail.subject == "Twój jednorazowy kod logowania do Pi-Plane: 123456"
        html = mail.alternatives[0][0]
        assert 'lang="pl"' in html
        assert "Wpisz go na stronie logowania" in html

    def test_someone_signing_up_gets_the_language_of_their_browser(self, mailoutbox):
        _send("new@example.com", accept_language="de-DE,de;q=0.9")

        assert mailoutbox[0].subject == "Ihr Einmalcode für die Pi-Plane-Anmeldung lautet 123456"

    def test_the_email_carries_the_code_to_type_and_no_link(self, mailoutbox):
        _send("new@example.com", token="654321", accept_language="pl")

        html = mailoutbox[0].alternatives[0][0]
        assert "654321" in html
        assert "href" not in html
        assert "new@example.com" in html

    def test_an_unsupported_browser_language_falls_back_to_english(self, mailoutbox):
        _send("new@example.com", accept_language="xx-YY")

        assert mailoutbox[0].subject == "Your one-time Pi-Plane login code is 123456"
