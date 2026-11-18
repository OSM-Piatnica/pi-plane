# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The sign-in code email is written in the language of the person it goes to."""

from unittest.mock import patch

import pytest

from plane.bgtasks.one_time_code_task import send_one_time_code
from plane.db.models import Profile
from plane.tests.factories import UserFactory
from plane.utils.email_i18n import LOCALES_DIR, language_from_accept_header

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


def _send(email, token="123456", accept_language=None, language=None, purpose="sign_in"):
    with patch("plane.bgtasks.one_time_code_task.get_email_configuration", return_value=CONFIG):
        send_one_time_code(
            email, f"one_time_code_{email}", token, accept_language=accept_language, language=language, purpose=purpose
        )


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

    def test_someone_signing_up_gets_the_language_picked_on_the_page(self, mailoutbox):
        # the browser says German, the language picked on the sign-up page wins
        _send("new@example.com", accept_language="de-DE,de;q=0.9", language="pl")

        assert mailoutbox[0].subject == "Twój jednorazowy kod logowania do Pi-Plane: 123456"
        assert 'lang="pl"' in mailoutbox[0].alternatives[0][0]

    def test_a_language_variant_gets_the_emails_of_its_language(self, mailoutbox):
        _send("new@example.com", language="pl-x-podlaski")

        assert mailoutbox[0].subject == "Twój jednorazowy kod logowania do Pi-Plane: 123456"

    @pytest.mark.parametrize("language", ["xx", "", "../en", "PL", 42])
    def test_a_picked_language_without_emails_falls_back_to_the_browser(self, mailoutbox, language):
        _send("new@example.com", accept_language="de", language=language)

        assert mailoutbox[0].subject == "Ihr Einmalcode für die Pi-Plane-Anmeldung lautet 123456"

    def test_a_known_user_keeps_the_language_of_their_profile(self, mailoutbox):
        user = UserFactory(email="known@example.com")
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.language = "de"
        profile.save()

        _send("known@example.com", language="pl")

        assert mailoutbox[0].subject == "Ihr Einmalcode für die Pi-Plane-Anmeldung lautet 123456"


@pytest.mark.unit
@pytest.mark.django_db
class TestSignUpCodeEmail:
    """The code that confirms the address of a sign-up is not worded as a sign-in code."""

    def test_english_says_sign_up_not_login(self, mailoutbox):
        _send("new@example.com", purpose="sign_up")

        mail = mailoutbox[0]
        assert mail.subject == "Your Pi-Plane sign-up code is 123456"
        html = mail.alternatives[0][0]
        assert "Confirm your email address for Pi-Plane" in html
        assert "Enter it on the sign-up page to create your account" in html
        text = mail.body.lower()
        assert "sign-in" not in text
        assert "login" not in text

    def test_the_sign_in_code_keeps_its_wording(self, mailoutbox):
        _send("new@example.com", purpose="sign_in")

        assert mailoutbox[0].subject == "Your one-time Pi-Plane login code is 123456"

    @pytest.mark.parametrize("language", sorted(path.stem for path in LOCALES_DIR.glob("*.json")))
    def test_every_language_has_its_own_sign_up_wording(self, mailoutbox, language):
        _send("new@example.com", language=language, purpose="sign_up")
        _send("new@example.com", language=language, purpose="sign_in")

        sign_up, sign_in = mailoutbox
        assert sign_up.subject != sign_in.subject
        assert "123456" in sign_up.subject
        sign_up_html = sign_up.alternatives[0][0]
        assert "654321" not in sign_up_html and "new@example.com" in sign_up_html
        assert sign_up_html != sign_in.alternatives[0][0]
