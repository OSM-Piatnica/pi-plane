# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The emails: every template still renders, nothing in them points at upstream Plane, and the mark is configurable."""

import re
from pathlib import Path

import pytest
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import override_settings

TEMPLATES = Path(__file__).resolve().parents[3] / "templates" / "emails"
NAMES = sorted(str(path.relative_to(TEMPLATES.parent)) for path in TEMPLATES.rglob("*.html"))

# Plane's own sites and accounts. The small state and priority icons of the work item emails are still hosted by Plane
# (see docs/branding-todo.md), which is why that one host is not in this list.
UPSTREAM = [
    "media.docs.plane.so",
    "https://plane.so",
    "planepowers",
    "github.com/makeplane",
    "plane.sh/",
    "forum.plane.so",
    "Plane Software",
]


@pytest.mark.unit
class TestEmailTemplates:
    def test_the_templates_are_found(self):
        assert len(NAMES) >= 15

    @pytest.mark.parametrize("name", NAMES)
    def test_every_template_renders(self, name):
        html = render_to_string(name, {"email_language": "en"})

        assert "<html" in html

    @pytest.mark.parametrize("name", NAMES)
    def test_no_template_points_at_upstream_plane(self, name):
        source = (TEMPLATES.parent / name).read_text(encoding="utf-8")
        # the licence notice at the top of a template is a comment and has to name the original authors
        source = re.sub(r"\{% comment %\}.*?\{% endcomment %\}", "", source, flags=re.S)

        assert [text for text in UPSTREAM if text in source] == []

    @pytest.mark.parametrize("name", NAMES)
    def test_links_and_cells_are_still_closed(self, name):
        source = (TEMPLATES.parent / name).read_text(encoding="utf-8")

        for tag in ("a", "p", "td", "tr", "table"):
            opened = len(re.findall(rf"<{tag}\b", source))
            closed = len(re.findall(rf"</{tag}\s*>", source))
            assert opened == closed, f"{name}: <{tag}> opened {opened} times, closed {closed}"


def _logo(variant="dark", width=120):
    return Template('{% load email_assets %}{% email_logo "' + variant + '" ' + str(width) + " %}").render(Context())


@pytest.mark.unit
class TestEmailLogo:
    def test_without_a_configured_image_the_name_is_set_in_type(self):
        with override_settings(EMAIL_LOGO_URL="", EMAIL_LOGO_URL_ON_DARK=""):
            dark, white = _logo("dark"), _logo("white")

        assert "<img" not in dark and "Pi-Plane" in dark and "#111111" in dark
        assert "<img" not in white and "Pi-Plane" in white and "#ffffff" in white

    def test_a_configured_image_is_used_for_its_background(self):
        with override_settings(
            EMAIL_LOGO_URL="https://cdn.example.com/dark.png",
            EMAIL_LOGO_URL_ON_DARK="https://cdn.example.com/white.png",
        ):
            dark, white = _logo("dark", 120), _logo("white", 150)

        assert 'src="https://cdn.example.com/dark.png"' in dark and 'width="120"' in dark
        assert 'src="https://cdn.example.com/white.png"' in white and 'width="150"' in white

    @pytest.mark.parametrize(
        "url", ["http://cdn.example.com/logo.png", "javascript:alert(1)", "//cdn.example.com/a.png"]
    )
    def test_only_a_secure_address_is_accepted(self, url):
        with override_settings(EMAIL_LOGO_URL=url):
            html = _logo("dark")

        assert "<img" not in html and url not in html

    def test_the_address_cannot_break_out_of_the_attribute(self):
        with override_settings(EMAIL_LOGO_URL='https://cdn.example.com/a.png" onerror="alert(1)'):
            html = _logo("dark")

        assert 'onerror="alert(1)"' not in html
