# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import re

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
# CSS variable names without the leading `--`; the web app drops the ones that are not themeable
TOKEN_NAME = re.compile(r"^[a-z0-9-]{1,64}$")


def clean_theme_data(data):
    """Returns (cleaned, errors) for a theme given as primary, background, dark_palette and overrides."""
    errors = {}
    cleaned = {}

    for field in ("primary", "background"):
        value = data.get(field)
        if not isinstance(value, str) or not HEX_COLOR.match(value):
            errors[field] = "Must be a hex colour like #4F8F7D."
        else:
            cleaned[field] = value.lower()

    dark_palette = data.get("dark_palette", False)
    if not isinstance(dark_palette, bool):
        errors["dark_palette"] = "Must be true or false."
    else:
        cleaned["dark_palette"] = dark_palette

    overrides = data.get("overrides") or {}
    if not isinstance(overrides, dict):
        errors["overrides"] = "Must be an object of token names and hex colours."
    else:
        bad = [
            token
            for token, value in overrides.items()
            if not TOKEN_NAME.match(str(token)) or not isinstance(value, str) or not HEX_COLOR.match(value)
        ]
        if bad:
            errors["overrides"] = f"Invalid tokens: {', '.join(sorted(map(str, bad)))}."
        else:
            cleaned["overrides"] = {token: value.lower() for token, value in overrides.items()}

    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        errors["name"] = "Required, up to 100 characters."
    else:
        cleaned["name"] = name.strip()

    return cleaned, errors
