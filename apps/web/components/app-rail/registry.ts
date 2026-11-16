/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAppRailApp, TAppRailAppKey } from "@plane/types";

/**
 * The apps of the app rail, in the order they are shown.
 *
 * This file holds no React code so the registry can be unit tested; icons and sidebars are in
 * `registry-ui.tsx`. How to add an app: `docs/app-rail.md`.
 */
export const APP_RAIL_APPS: readonly TAppRailApp[] = [
  {
    key: "projects",
    i18n_label: "projects",
    i18n_switch_label: "app_rail.switch_to.projects",
    // the default app: home, projects, views, analytics and every other path no app claims
    routeSegments: [],
    isDefault: true,
    getHref: (workspaceSlug) => `/${workspaceSlug}/`,
    isEnabled: () => true,
  },
];

export const getAppRailApp = (key: TAppRailAppKey): TAppRailApp | undefined =>
  APP_RAIL_APPS.find((app) => app.key === key);
