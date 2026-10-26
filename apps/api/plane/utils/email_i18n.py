# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Text of the notification emails in the recipient's language.

The strings live in ``plane/email_locales/<language>.json`` (nested objects, addressed by dotted keys). A value is
either a string or, for counted phrases, an object with the CLDR plural categories (``one``, ``few``, ``many``,
``other``). ``{name}`` placeholders are filled from the keyword arguments; a missing string falls back to English.
"""

import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "email_locales"
DEFAULT_LANGUAGE = "en"

# Profile language codes without a file of their own share the file of the language they are a variant of
LANGUAGE_ALIASES = {"pl-x-podlaski": "pl"}

# Plural rule family per language (CLDR); languages without an entry have the plain one/other rule
_SINGLE_FORM = {"ja", "ko", "zh-CN", "zh-TW", "vi-VN", "id"}
_EAST_SLAVIC = {"ru", "ua"}
_WEST_SLAVIC_FEW_MANY = {"pl", "pl-x-podlaski"}
_CZECH_SLOVAK = {"cs", "sk"}
_ONE_FEW_OTHER = {"ro"}
_ZERO_AND_ONE = {"fr", "pt-BR", "pt-PT"}


def plural_category(language, count):
    """CLDR plural category of a whole number for the language."""
    if language in _SINGLE_FORM:
        return "other"
    if language in _EAST_SLAVIC:
        if count % 10 == 1 and count % 100 != 11:
            return "one"
        if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
            return "few"
        return "many"
    if language in _WEST_SLAVIC_FEW_MANY:
        if count == 1:
            return "one"
        if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
            return "few"
        return "many"
    if language in _CZECH_SLOVAK:
        if count == 1:
            return "one"
        return "few" if 2 <= count <= 4 else "other"
    if language in _ONE_FEW_OTHER:
        if count == 1:
            return "one"
        return "few" if count == 0 or 1 <= count % 100 <= 19 else "other"
    if language in _ZERO_AND_ONE:
        return "one" if count in (0, 1) else "other"
    return "one" if count == 1 else "other"


def normalize_language(language):
    """The language the emails are written in for a profile language code; English when there are none."""
    language = LANGUAGE_ALIASES.get(language or "", language or "")
    return language if (LOCALES_DIR / f"{language}.json").is_file() else DEFAULT_LANGUAGE


def _flatten(node, prefix=""):
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and not (value.keys() <= {"zero", "one", "two", "few", "many", "other"}):
            yield from _flatten(value, f"{path}.")
        else:
            yield path, value


@lru_cache(maxsize=None)
def _strings(language):
    with open(LOCALES_DIR / f"{language}.json", encoding="utf-8") as handle:
        return dict(_flatten(json.load(handle)))


def translate(language, key, count=None, **params):
    """The string for ``key`` in the language, with the plural form for ``count`` and the placeholders filled."""
    language = normalize_language(language)
    value = _strings(language).get(key)
    if value is None:
        value = _strings(DEFAULT_LANGUAGE)[key]
    if isinstance(value, dict):
        category = plural_category(language, count or 0)
        value = value.get(category) or value.get("other") or next(iter(value.values()))
    if count is not None:
        params["count"] = count
    return value.format(**params)


def user_language(user):
    """The language the emails to the user are written in: the language of their profile."""
    profile = getattr(user, "profile", None)  # a user without a profile row raises an AttributeError subclass
    return normalize_language(getattr(profile, "language", None))


# Browser language tags whose email file has another name
_BROWSER_LANGUAGES = {
    "uk": "ua",
    "ka": "ka-ge",
    "tr": "tr-TR",
    "vi": "vi-VN",
    "zh-hans": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-sg": "zh-CN",
    "zh-hant": "zh-TW",
    "zh-tw": "zh-TW",
    "zh-hk": "zh-TW",
    "zh-mo": "zh-TW",
    "pt-br": "pt-BR",
    "pt-pt": "pt-PT",
    "pt": "pt-BR",
}


def language_from_accept_header(header):
    """The language of the first tag of an ``Accept-Language`` header that has emails of its own, else English.

    For people who have no profile yet, such as someone signing up, whose only hint is their browser.
    """
    for part in (header or "").split(","):
        tag = part.split(";")[0].strip().lower()
        if not tag or tag == "*":
            continue
        parts = tag.split("-")
        # the most specific match first: zh-hant-tw, zh-hant, zh
        for length in range(len(parts), 0, -1):
            prefix = "-".join(parts[:length])
            language = _BROWSER_LANGUAGES.get(prefix, prefix)
            if (LOCALES_DIR / f"{language}.json").is_file():
                return language
            if language in LANGUAGE_ALIASES:
                return normalize_language(language)
    return DEFAULT_LANGUAGE
