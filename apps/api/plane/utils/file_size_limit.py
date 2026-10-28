# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The largest file a person may upload, as the instance administrator set it.

The administrator changes it on the General page of the admin app; it is stored as the instance configuration
``FILE_SIZE_LIMIT`` (bytes). Until one is saved, or when the value is empty, the environment variable
``FILE_SIZE_LIMIT`` (default 5 MiB) applies. ``FILE_SIZE_LIMIT_MAX`` is the ceiling: the proxy in front refuses a
request body above it, so the instance cannot be set higher.

A smaller limit applies to new uploads only. Files that are already stored are never touched.
"""

from django.conf import settings

CONFIG_KEY = "FILE_SIZE_LIMIT"
# Smaller than this is not a useful limit (a typical avatar is several hundred KB)
MIN_FILE_SIZE_LIMIT = 1024 * 1024


def get_file_size_limit_max() -> int:
    """The ceiling the deployment allows: never below the default limit."""
    return max(int(settings.FILE_SIZE_LIMIT_MAX), int(settings.FILE_SIZE_LIMIT))


def parse_file_size_limit(raw) -> int | None:
    """A whole number of bytes, or None when `raw` is empty or not one."""
    text = str(raw if raw is not None else "").strip()
    if not text.isdecimal():
        return None
    value = int(text)
    return value if value > 0 else None


def get_file_size_limit() -> int:
    """The limit in bytes: the saved setting, else the environment default, within the allowed range."""
    default = int(settings.FILE_SIZE_LIMIT)
    value = None
    if settings.SKIP_ENV_VAR:
        # Imported here: plane.license models import this package's siblings at start-up
        from plane.license.models import InstanceConfiguration

        saved = InstanceConfiguration.objects.filter(key=CONFIG_KEY).values_list("value", flat=True).first()
        value = parse_file_size_limit(saved)
    if value is None:
        return default
    return max(MIN_FILE_SIZE_LIMIT, min(value, get_file_size_limit_max()))
