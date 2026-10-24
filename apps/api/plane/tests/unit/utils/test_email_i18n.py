# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The strings of the notification emails: plural rules, fallbacks and the consistency of the locale files."""

import json
import re

import pytest
from django.template import Context, Template

from plane.utils import email_i18n
from plane.utils.email_i18n import LOCALES_DIR, normalize_language, plural_category, translate

PLURAL_CATEGORIES = {"zero", "one", "two", "few", "many", "other"}
LOCALE_FILES = sorted(path.stem for path in LOCALES_DIR.glob("*.json"))
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _flat(node, prefix=""):
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and not value.keys() <= PLURAL_CATEGORIES:
            yield from _flat(value, f"{path}.")
        else:
            yield path, value


def _load(language):
    with open(LOCALES_DIR / f"{language}.json", encoding="utf-8") as handle:
        return dict(_flat(json.load(handle)))


@pytest.mark.unit
class TestPluralCategory:
    @pytest.mark.parametrize(
        "language, expected",
        [
            ("en", {1: "one", 0: "other", 2: "other", 21: "other"}),
            ("de", {1: "one", 2: "other"}),
            ("fr", {0: "one", 1: "one", 2: "other"}),
            ("pl", {1: "one", 2: "few", 4: "few", 5: "many", 12: "many", 22: "few", 25: "many", 112: "many"}),
            ("ru", {1: "one", 21: "one", 2: "few", 24: "few", 5: "many", 11: "many", 12: "many", 111: "many"}),
            ("ua", {1: "one", 3: "few", 11: "many", 101: "one"}),
            ("cs", {1: "one", 2: "few", 4: "few", 5: "other", 0: "other"}),
            ("sk", {1: "one", 3: "few", 6: "other"}),
            ("ro", {1: "one", 0: "few", 2: "few", 19: "few", 20: "other", 101: "few"}),
            ("ja", {1: "other", 5: "other"}),
            ("zh-CN", {1: "other"}),
        ],
    )
    def test_follows_the_cldr_rule_of_the_language(self, language, expected):
        for count, category in expected.items():
            assert plural_category(language, count) == category, (language, count)


@pytest.mark.unit
class TestTranslate:
    def test_fills_the_placeholders(self):
        assert translate("en", "issue_updates.title", identifier="PRJ-1") == "PRJ-1 updates"

    def test_picks_the_plural_form_of_the_language(self):
        assert translate("pl", "digest.updates_count", count=1) == "1 aktualizacja"
        assert translate("pl", "digest.updates_count", count=3) == "3 aktualizacje"
        assert translate("pl", "digest.updates_count", count=5) == "5 aktualizacji"
        assert translate("en", "digest.updates_count", count=1) == "1 update"
        assert translate("en", "digest.updates_count", count=2) == "2 updates"

    def test_unknown_or_missing_language_is_english(self):
        assert translate("xx", "due_reminder.cta") == "View my work items"
        assert translate(None, "due_reminder.cta") == "View my work items"

    def test_a_variant_without_its_own_file_uses_its_base_language(self):
        assert normalize_language("pl-x-podlaski") == "pl"
        assert translate("pl-x-podlaski", "due_reminder.cta") == translate("pl", "due_reminder.cta")

    def test_a_key_missing_in_a_language_falls_back_to_english(self, monkeypatch):
        monkeypatch.setattr(email_i18n, "_strings", lambda language: {} if language == "pl" else _load("en"))
        assert translate("pl", "due_reminder.cta") == "View my work items"


@pytest.mark.unit
class TestLocaleFiles:
    def test_every_web_locale_has_a_file_or_an_alias(self):
        web_locales = {"bg", "cs", "de", "en", "es", "fr", "id", "it", "ja", "ka-ge", "ko", "nl", "pl", "pl-x-podlaski"}
        web_locales |= {"pt-BR", "pt-PT", "ro", "ru", "sk", "tr-TR", "ua", "vi-VN", "zh-CN", "zh-TW"}
        covered = set(LOCALE_FILES) | set(email_i18n.LANGUAGE_ALIASES)
        assert web_locales <= covered

    @pytest.mark.parametrize("language", LOCALE_FILES)
    def test_has_the_keys_of_english(self, language):
        assert sorted(_load(language)) == sorted(_load("en"))

    @pytest.mark.parametrize("language", [name for name in LOCALE_FILES if name != "en"])
    def test_keeps_the_placeholders_of_english(self, language):
        english, strings = _load("en"), _load(language)
        for key, english_value in english.items():
            value = strings[key]
            if isinstance(english_value, dict):
                english_value = english_value["other"]
            forms = value.values() if isinstance(value, dict) else [value]
            # the plural form may drop {count} (a language can write "one" without the number), nothing else
            expected = set(PLACEHOLDER.findall(english_value)) - {"count"}
            for form in forms:
                assert expected <= set(PLACEHOLDER.findall(form)), (language, key, form)
                assert set(PLACEHOLDER.findall(form)) <= set(PLACEHOLDER.findall(english_value)) | {"count"}, (
                    language,
                    key,
                    form,
                )

    @pytest.mark.parametrize("language", LOCALE_FILES)
    def test_has_every_plural_form_the_language_needs(self, language):
        for key, value in _load(language).items():
            if not isinstance(value, dict):
                continue
            assert "other" in value or all(plural_category(language, n) in value for n in range(0, 1200)), (
                language,
                key,
            )

    @pytest.mark.parametrize("language", LOCALE_FILES)
    def test_markup_is_balanced_and_formats_cleanly(self, language):
        for key, value in _load(language).items():
            for form in value.values() if isinstance(value, dict) else [value]:
                assert len(re.findall(r"<(strong|a|span)\b", form)) == len(re.findall(r"</(strong|a|span)>", form)), (
                    language,
                    key,
                )
                form.format(**{name: "x" for name in PLACEHOLDER.findall(form)}, count=1)


@pytest.mark.unit
class TestTemplateTag:
    def test_escapes_the_values_but_not_the_markup_of_the_string(self):
        template = Template('{% load email_i18n %}{% etr "project_addition.intro" inviter=a project=b workspace=c %}')
        html = template.render(Context({"a": "<i>Ann</i>", "b": "P&Q", "c": "W", "email_language": "en"}))
        assert "&lt;i&gt;Ann&lt;/i&gt;" in html
        assert "<strong>P&amp;Q</strong>" in html

    def test_gives_links_the_inline_style(self):
        template = Template(
            '{% load email_i18n %}{% etr "digest.footer" preferences_url=url link_style="color: red" %}'
        )
        html = template.render(Context({"url": "http://x/?a=1&b=2", "email_language": "en"}))
        assert '<a style="color: red" href="http://x/?a=1&amp;b=2">' in html

    def test_translates_the_priority_names_and_leaves_other_values(self):
        template = Template("{% load email_i18n %}{% etr_priority p %}")
        assert template.render(Context({"p": "high", "email_language": "pl"})) == "Wysoki"
        assert template.render(Context({"p": "custom", "email_language": "pl"})) == "custom"
