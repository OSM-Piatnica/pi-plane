/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TPowerKCommandConfig } from "@/components/power-k/core/types";
import { APP_RAIL_APP_ICONS } from "./registry-icons";
import { buildAppRailSwitchCommands } from "./switch-commands";
import { useAppRailApps } from "./use-app-rail-apps";

/** App switching commands for the command palette; empty while only one app is enabled */
export const useAppRailPowerKCommands = (): TPowerKCommandConfig[] => {
  const { enabledApps } = useAppRailApps();

  return buildAppRailSwitchCommands(enabledApps, APP_RAIL_APP_ICONS);
};
