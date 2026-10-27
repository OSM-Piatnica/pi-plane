# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from plane.utils.email_i18n import translate

register = template.Library()


@register.simple_tag(takes_context=True)
def etr(context, key, count=None, link_style=None, span_style=None, **params):
    """Text of an email in the language the task put in the context as ``email_language``.

    ``{% etr "issue_updates.more" count=3 %}``. The strings are ours, so they may carry markup such as ``<strong>`` or
    ``<a href="{url}">``; the values filled into their placeholders are escaped. ``link_style`` is an inline style
    given to every link of the string and ``span_style`` to every plain ``<span>``, because email clients ignore style
    sheets.
    """
    escaped = {name: conditional_escape(value) for name, value in params.items()}
    text = translate(context.get("email_language"), key, count=count, **escaped)
    if link_style:
        text = text.replace("<a ", f'<a style="{conditional_escape(link_style)}" ')
    if span_style:
        text = text.replace("<span>", f'<span style="{conditional_escape(span_style)}">')
    return mark_safe(text)  # noqa: S308


@register.simple_tag(takes_context=True)
def etr_priority(context, value):
    """Name of a priority ("high") in the language of the email; other values are shown as they are."""
    key = f"priority.{value}"
    if str(value) in ("urgent", "high", "medium", "low", "none"):
        return translate(context.get("email_language"), key)
    return value
