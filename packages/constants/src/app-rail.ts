/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * First path segments after the workspace slug that belong to no rail app: on these routes
 * no app is highlighted. Settings has its own rail item, notifications live in the top bar.
 */
export const APP_RAIL_NON_APP_ROUTE_SEGMENTS: readonly string[] = ["settings", "notifications"];

/**
 * App switching shortcuts are the key sequence `g` + position in the rail (`g1`, `g2`, ...).
 * `g` is already the "go to" prefix of the command palette and no command uses a digit after it.
 */
export const APP_RAIL_SWITCH_KEY_SEQUENCE_PREFIX = "g";

/** Apps beyond this position in the rail get a command palette entry without a shortcut */
export const APP_RAIL_MAX_SWITCH_SHORTCUTS = 9;

/**
 * Prefix of the `WorkspaceUserPreference` key that holds a user's order (`sort_order`) and hidden
 * state (`is_pinned` false) of a rail app, for example `app_rail:approvals`. The API accepts the
 * prefix only with a known app key (`apps/api/plane/utils/app_rail.py`).
 */
export const APP_RAIL_PREFERENCE_KEY_PREFIX = "app_rail:";

/** `localStorage` key of the app a user last used in a workspace: this prefix plus the workspace slug */
export const APP_RAIL_LAST_USED_APP_STORAGE_KEY_PREFIX = "APP_RAIL_LAST_APP_";
