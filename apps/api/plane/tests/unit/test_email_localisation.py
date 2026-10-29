# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The account, invitation, password, webhook and export emails are written in the recipient's language."""

import io
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from django.template.loader import render_to_string
from django.utils.html import format_html

from plane.bgtasks.analytic_plot_export import send_export_email
from plane.bgtasks.forgot_password_task import forgot_password
from plane.bgtasks.user_activation_email_task import user_activation_email
from plane.bgtasks.user_deactivation_email_task import user_deactivation_email
from plane.bgtasks.user_email_update_task import send_email_update_confirmation, send_email_update_one_time_code
from plane.bgtasks.webhook_task import send_webhook_deactivation_email
from plane.bgtasks.workspace_invitation_task import workspace_invitation
from plane.db.models import Profile, Webhook, WorkspaceMember, WorkspaceMemberInvite
from plane.tests.factories import UserFactory, WorkspaceFactory
from plane.utils.email import generate_plain_text_from_html
from plane.utils.email_i18n import translate

LOCALES = Path(__file__).resolve().parents[2] / "email_locales"
TEMPLATES = Path(__file__).resolve().parents[3] / "templates" / "emails"
LANGUAGES = sorted(path.stem for path in LOCALES.glob("*.json"))
CONFIG = ("localhost", "", "", "25", "0", "0", "noreply@example.com")
# What each of the emails in this file needs in its context, besides the language
SAMPLE_CONTEXT = {
    "emails/auth/forgot_password.html": {"forgot_password_url": "https://x/reset", "email": "a@b.c"},
    "emails/invitations/workspace_invitation.html": {
        "first_name": "Ann",
        "workspace_name": "Acme",
        "abs_url": "https://x/invite",
        "email": "a@b.c",
    },
    "emails/exports/analytics.html": {},
    "emails/user/user_activation.html": {"email": "a@b.c", "profile_url": "https://x/profile"},
    "emails/user/user_deactivation.html": {"email": "a@b.c", "login_url": "https://x/login"},
    "emails/user/email_updated.html": {"email": "a@b.c", "email_strong": format_html("<strong>{}</strong>", "a@b.c")},
    "emails/notifications/webhook-deactivate.html": {
        "email": "a@b.c",
        "message": "Webhook https://hooks.example.com/x has been deactivated.",
        "webhook_url": "https://x/webhook",
    },
}


def _flatten(node, prefix=""):
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and not value.keys() <= {"zero", "one", "two", "few", "many", "other"}:
            yield from _flatten(value, f"{path}.")
        else:
            yield path, value


def _strings(language):
    return dict(_flatten(json.loads((LOCALES / f"{language}.json").read_text(encoding="utf-8"))))


def _visible(html):
    return re.sub(r"\s+", " ", generate_plain_text_from_html(html)).strip()


@pytest.mark.unit
class TestTheTexts:
    @pytest.mark.parametrize("language", [code for code in LANGUAGES if code != "en"])
    def test_every_language_has_every_string_of_english_with_the_same_placeholders(self, language):
        english, strings = _strings("en"), _strings(language)

        assert sorted(set(english) - set(strings)) == []
        for key, text in english.items():
            if isinstance(text, str):
                assert sorted(re.findall(r"\{(\w+)\}", text)) == sorted(re.findall(r"\{(\w+)\}", strings[key])), (
                    f"{language}: {key}"
                )

    @pytest.mark.parametrize("path", sorted(TEMPLATES.rglob("*.html")), ids=lambda p: str(p.relative_to(TEMPLATES)))
    def test_every_string_a_template_asks_for_exists(self, path):
        keys = re.findall(r'\{%\s*etr\s+"([\w.]+)"', path.read_text(encoding="utf-8"))
        english = _strings("en")

        assert [key for key in keys if key not in english] == []


@pytest.mark.unit
class TestTheTemplates:
    @pytest.mark.parametrize("name", sorted(SAMPLE_CONTEXT))
    @pytest.mark.parametrize("language", [code for code in LANGUAGES if code != "en"])
    def test_a_template_follows_the_language_of_its_context(self, name, language):
        english = render_to_string(name, {**SAMPLE_CONTEXT[name], "email_language": "en"})
        translated = render_to_string(name, {**SAMPLE_CONTEXT[name], "email_language": language})

        assert _visible(english) != _visible(translated)

    @pytest.mark.parametrize("name", sorted(SAMPLE_CONTEXT))
    def test_a_template_without_a_language_is_in_english(self, name):
        assert _visible(render_to_string(name, SAMPLE_CONTEXT[name])) == _visible(
            render_to_string(name, {**SAMPLE_CONTEXT[name], "email_language": "en"})
        )

    def test_the_address_in_a_note_cannot_inject_markup(self):
        html = render_to_string(
            "emails/auth/forgot_password.html",
            {
                **SAMPLE_CONTEXT["emails/auth/forgot_password.html"],
                "email": "<script>x</script>@b.c",
                "email_language": "de",
            },
        )

        assert "<script>x</script>" not in html


def _user(language="en", **kwargs):
    user = UserFactory(**kwargs)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.language = language
    profile.save()
    return user


def _subject(language, key, **params):
    return translate(language, key, **params)


@pytest.mark.unit
@pytest.mark.django_db
class TestTheTasks:
    @pytest.fixture(autouse=True)
    def mail_settings(self):
        modules = [
            "forgot_password_task",
            "workspace_invitation_task",
            "user_activation_email_task",
            "user_deactivation_email_task",
            "user_email_update_task",
            "webhook_task",
            "analytic_plot_export",
        ]
        patches = [patch(f"plane.bgtasks.{m}.get_email_configuration", return_value=CONFIG) for m in modules]
        for p in patches:
            p.start()
        yield
        for p in patches:
            p.stop()

    def test_a_forgotten_password_email_is_in_the_language_of_the_profile_and_english_without_an_account(
        self, mailoutbox
    ):
        _user("de", email="ada@example.com")

        forgot_password("Ada", "ada@example.com", "uid", "token", "https://plane.example.com")
        forgot_password("Eve", "stranger@example.com", "uid", "token", "https://plane.example.com")

        assert mailoutbox[0].subject == _subject("de", "forgot_password.subject")
        assert mailoutbox[1].subject == _subject("en", "forgot_password.subject")
        assert "Passwort" in mailoutbox[0].alternatives[0][0]

    def test_an_invitation_uses_the_profile_of_an_invitee_who_has_an_account_and_the_invitation_otherwise(
        self, mailoutbox
    ):
        workspace = WorkspaceFactory(name="Acme")
        inviter = _user("en", email="boss@example.com", first_name="Boss")
        WorkspaceMember.objects.create(workspace=workspace, member=inviter, role=20)
        _user("fr", email="known@example.com")
        WorkspaceMemberInvite.objects.create(workspace=workspace, email="known@example.com", token="t1", language="pl")
        WorkspaceMemberInvite.objects.create(workspace=workspace, email="new@example.com", token="t2", language="pl")

        workspace_invitation("known@example.com", str(workspace.id), "t1", "https://plane.example.com", inviter.email)
        workspace_invitation("new@example.com", str(workspace.id), "t2", "https://plane.example.com", inviter.email)

        expected = {"inviter": "Boss", "workspace": "Acme"}
        assert mailoutbox[0].subject == _subject("fr", "workspace_invitation.subject", **expected)
        assert mailoutbox[1].subject == _subject("pl", "workspace_invitation.subject", **expected)
        assert _subject("fr", "workspace_invitation.subject", **expected) != _subject(
            "pl", "workspace_invitation.subject", **expected
        )

    def test_the_account_emails_follow_the_profile(self, mailoutbox):
        user = _user("ja", email="ada@example.com", first_name="Ada")

        user_activation_email("https://plane.example.com", str(user.id))
        user_deactivation_email("https://plane.example.com", str(user.id))

        assert mailoutbox[0].subject == _subject("ja", "account_activated.subject", name="Ada")
        assert mailoutbox[1].subject == _subject("ja", "account_deactivated.subject", name="Ada")
        assert "Ada" in mailoutbox[0].subject

    def test_the_email_change_emails_follow_the_profile_when_they_are_told_whose_it_is(self, mailoutbox):
        user = _user("es", email="ada@example.com")

        send_email_update_one_time_code("new@example.com", "123456", str(user.id))
        send_email_update_confirmation("new@example.com", str(user.id))
        send_email_update_confirmation("new@example.com")

        assert mailoutbox[0].subject == _subject("es", "email_update_code.subject")
        assert mailoutbox[1].subject == _subject("es", "email_updated.subject")
        assert mailoutbox[2].subject == _subject("en", "email_updated.subject")
        assert "<strong>new@example.com</strong>" in mailoutbox[1].alternatives[0][0]

    def test_the_webhook_email_has_its_message_in_the_language_of_the_owner(self, mailoutbox):
        workspace = WorkspaceFactory()
        owner = _user("ru", email="owner@example.com")
        webhook = Webhook.objects.create(workspace=workspace, url="https://hooks.example.com/x")

        send_webhook_deactivation_email(str(webhook.id), str(owner.id), "https://plane.example.com", "failed")

        assert mailoutbox[0].subject == _subject("ru", "webhook_deactivated.subject")
        message = _subject("ru", "webhook_deactivated.message", url="https://hooks.example.com/x")
        assert message in mailoutbox[0].alternatives[0][0]

    def test_the_export_email_follows_the_profile_of_whoever_asked(self, mailoutbox):
        _user("it", email="ada@example.com")

        send_export_email("ada@example.com", "acme", io.StringIO("a,b\n1,2\n"), [])

        assert mailoutbox[0].subject == _subject("it", "analytics_export.subject")
