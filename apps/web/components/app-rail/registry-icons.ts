/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType } from "react";
import { InitiativeOutline, Projects } from "@makeplane/propel/icons";
import type { TAppRailAppKey } from "@plane/types";

export type TAppRailAppIcon = ComponentType<{ className?: string }>;

/**
 * Icon of each rail app: shown in the rail (at `size-5`) and next to the app's command palette
 * entry. Keyed by `TAppRailAppKey`, so an app added to the union does not compile without one.
 */
export const APP_RAIL_APP_ICONS: Record<TAppRailAppKey, TAppRailAppIcon> = {
  projects: Projects,
  initiatives: InitiativeOutline,
};
