# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The brand mark of the emails: one place instead of a hard-coded image address in every template."""

from django import template
from django.conf import settings
from django.utils.html import format_html

register = template.Library()

# "dark" is the mark for light backgrounds, "white" the one for the dark header of the digest-style emails
_WORDMARK_COLORS = {"dark": "#111111", "white": "#ffffff"}


def _logo_url(variant):
    url = settings.EMAIL_LOGO_URL_ON_DARK if variant == "white" else settings.EMAIL_LOGO_URL
    # an image in an email has to be reachable from the recipient's mail client: only a secure address will do
    return url if isinstance(url, str) and url.startswith("https://") else ""


@register.simple_tag
def email_logo(variant="dark", width=120):
    """
    The Pi-Plane mark. An image when ``EMAIL_LOGO_URL`` (light backgrounds) or ``EMAIL_LOGO_URL_ON_DARK`` (the dark
    header) names one; otherwise the name set in type, which needs no hosting and cannot show up as a broken image.
    """
    url = _logo_url(variant)
    if url:
        return format_html(
            '<img src="{}" width="{}" alt="Pi-Plane" border="0" '
            'style="height: auto; display: block; margin: 0 auto" />',
            url,
            width,
        )
    color = _WORDMARK_COLORS.get(variant, _WORDMARK_COLORS["dark"])
    align = "left" if variant == "white" else "center"
    return format_html(
        '<span style="display: block; font-family: Arial, Helvetica, sans-serif; font-size: 26px; line-height: 32px; '
        'font-weight: 700; letter-spacing: 0.5px; color: {}; text-align: {}">Pi-Plane</span>',
        color,
        align,
    )
