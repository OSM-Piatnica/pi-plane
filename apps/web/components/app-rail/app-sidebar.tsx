/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType } from "react";
import type { TAppRailAppKey } from "@plane/types";
import { ProjectAppSidebar } from "@/app/(all)/[workspaceSlug]/(projects)/_sidebar";

/**
 * Contextual sidebar of each rail app. An app without an entry has no sidebar.
 *
 * Kept apart from the rest of the registry on purpose: sidebars pull in most of the app, and
 * only an app's layout may import this module. Importing it from the rail or the command
 * palette would create an import cycle through the sidebars.
 */
const APP_RAIL_APP_SIDEBARS: Partial<Record<TAppRailAppKey, ComponentType>> = {
  projects: ProjectAppSidebar,
};

/** The sidebar registered for a rail app, for use in that app's layout */
export function AppRailAppSidebar({ appKey }: { appKey: TAppRailAppKey }) {
  const Sidebar = APP_RAIL_APP_SIDEBARS[appKey];
  return Sidebar ? <Sidebar /> : null;
}
