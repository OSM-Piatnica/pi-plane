# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
How many messages to the admins of a workspace one person may send within an hour.

The deployment sets the default (``ADMIN_MESSAGE_LIMIT_PER_HOUR`` in the environment of the API); the instance admin can
change it in the admin app, which saves ``ADMIN_MESSAGE_LIMIT`` and wins over the environment. An empty saved value
means "the default of the deployment".
"""

import os

from plane.utils.file_size_limit import get_saved_number

SAVED_KEY = "ADMIN_MESSAGE_LIMIT"
ENV_KEY = "ADMIN_MESSAGE_LIMIT_PER_HOUR"
BUILT_IN_LIMIT = 5
MIN_ADMIN_MESSAGE_LIMIT = 1
MAX_ADMIN_MESSAGE_LIMIT = 100


def _clamp(value):
    return max(MIN_ADMIN_MESSAGE_LIMIT, min(value, MAX_ADMIN_MESSAGE_LIMIT))


def get_deployment_admin_message_limit() -> int:
    """What the deployment sets; a value that is not a whole number falls back to the built-in one."""
    raw = os.environ.get(ENV_KEY, "").strip()
    return _clamp(int(raw)) if raw.isdigit() else BUILT_IN_LIMIT


def get_admin_message_limit() -> int:
    saved = get_saved_number(SAVED_KEY)
    return get_deployment_admin_message_limit() if saved is None else _clamp(saved)
