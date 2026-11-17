# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keys of the apps of the web app's rail, for validating what a user stores about them.

The web app owns the registry (``apps/web/components/app-rail/registry.ts``, keys in
``packages/types/src/app-rail.ts``); a unit test of the web app compares its keys with this list.
See ``docs/app-rail.md``.
"""

APP_RAIL_APP_KEYS = ("projects",)

# ``WorkspaceUserPreference.key`` of a rail app: order (``sort_order``) and hidden state (``is_pinned`` false)
APP_RAIL_PREFERENCE_KEY_PREFIX = "app_rail:"


def is_app_rail_app_key(key):
    return isinstance(key, str) and key in APP_RAIL_APP_KEYS


def is_app_rail_preference_key(key):
    return (
        isinstance(key, str)
        and key.startswith(APP_RAIL_PREFERENCE_KEY_PREFIX)
        and is_app_rail_app_key(key[len(APP_RAIL_PREFERENCE_KEY_PREFIX) :])
    )
