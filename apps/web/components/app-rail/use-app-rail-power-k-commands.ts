/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import type { TPowerKCommandConfig } from "@/components/power-k/core/types";
import { AppRailVisibilityContext } from "@/lib/app-rail/context";
import { APP_RAIL_APP_ICONS } from "./registry-icons";
import { buildAppRailSwitchCommands } from "./switch-commands";
import { useAppRailApps } from "./use-app-rail-apps";

/** App rail commands for the command palette; empty while only one app is enabled */
export const useAppRailPowerKCommands = (): TPowerKCommandConfig[] => {
  const { enabledApps } = useAppRailApps();
  // read the context directly: the palette is also mounted outside a workspace (profile
  // settings), where there is no rail and `useAppRailVisibility` would throw
  const railVisibility = useContext(AppRailVisibilityContext);

  return buildAppRailSwitchCommands(
    enabledApps,
    APP_RAIL_APP_ICONS,
    railVisibility && { isCollapsed: railVisibility.isCollapsed, toggle: railVisibility.toggleAppRail }
  );
};
