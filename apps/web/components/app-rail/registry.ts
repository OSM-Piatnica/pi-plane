/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAppRailApp, TAppRailAppKey } from "@plane/types";

/**
 * The apps of the app rail. The order of the entries is the order in the rail.
 *
 * Typed as a record over `TAppRailAppKey`, so a key added to the union does not compile until
 * the app is registered here (and each entry's `key` has to match its property name).
 *
 * This file holds no React code so the registry can be unit tested; icons are in
 * `registry-icons.ts`, sidebars in `app-sidebar.tsx`. How to add an app: `docs/app-rail.md`.
 */
const APP_RAIL_APP_DEFINITIONS: { [TKey in TAppRailAppKey]: TAppRailApp & { key: TKey } } = {
  projects: {
    key: "projects",
    i18n_label: "projects",
    i18n_switch_label: "app_rail.switch_to.projects",
    // the default app: home, projects, views, analytics and every other path no app claims
    routeSegments: [],
    isDefault: true,
    getHref: (workspaceSlug) => `/${workspaceSlug}/`,
    isEnabled: () => true,
  },
};

/** The registered apps, in rail order */
export const APP_RAIL_APPS: readonly TAppRailApp[] = Object.values(APP_RAIL_APP_DEFINITIONS);

export const getAppRailApp = (key: TAppRailAppKey): TAppRailApp => APP_RAIL_APP_DEFINITIONS[key];
