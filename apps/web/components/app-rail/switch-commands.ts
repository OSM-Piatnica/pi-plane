/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType } from "react";
import type { TAppRailApp, TAppRailAppKey } from "@plane/types";
import { getAppRailSwitchKeySequence, hasMultipleAppRailApps } from "@plane/utils";
import type { TPowerKCommandConfig } from "@/components/power-k/core/types";

export const APP_RAIL_SWITCH_COMMAND_ID_PREFIX = "switch_app_";
export const APP_RAIL_TOGGLE_COMMAND_ID = "toggle_app_rail";

type TAppRailIcons = Partial<Record<TAppRailAppKey, ComponentType<{ className?: string }>>>;

/** Docking state of the rail, when the palette is mounted inside a workspace */
export type TAppRailDocking = {
  isCollapsed: boolean;
  toggle: () => void;
};

/**
 * Command palette entries of the app rail:
 *
 * - one entry per enabled app that switches to it, with the key sequence of the app's position
 *   in the rail (`g1`, `g2`, ...);
 * - "Dock app rail" / "Undock app rail". An undocked rail is not rendered at all, so its own
 *   right-click menu cannot bring it back: this entry is the way back.
 *
 * Returns nothing with fewer than two enabled apps. The commands must be absent then, not just
 * invisible: the keyboard shortcuts dialog lists every registered command that has a shortcut.
 */
export const buildAppRailSwitchCommands = (
  enabledApps: readonly TAppRailApp[],
  icons: TAppRailIcons = {},
  docking?: TAppRailDocking
): TPowerKCommandConfig[] => {
  if (!hasMultipleAppRailApps(enabledApps)) return [];

  const commands: TPowerKCommandConfig[] = enabledApps.map((app, index) => ({
    id: `${APP_RAIL_SWITCH_COMMAND_ID_PREFIX}${app.key}`,
    type: "action",
    group: "navigation",
    i18n_title: app.i18n_switch_label,
    icon: icons[app.key],
    keySequence: getAppRailSwitchKeySequence(index),
    action: (ctx) => {
      const workspaceSlug = ctx.params.workspaceSlug?.toString();
      if (workspaceSlug) ctx.router.push(app.getHref(workspaceSlug));
    },
    isEnabled: (ctx) => Boolean(ctx.params.workspaceSlug?.toString()),
    isVisible: (ctx) => Boolean(ctx.params.workspaceSlug?.toString()),
    closeOnSelect: true,
  }));

  if (docking)
    commands.push({
      id: APP_RAIL_TOGGLE_COMMAND_ID,
      type: "action",
      group: "miscellaneous",
      i18n_title: docking.isCollapsed ? "app_text.navigation.dock_app_rail" : "app_text.navigation.undock_app_rail",
      action: () => docking.toggle(),
      isEnabled: () => true,
      isVisible: () => true,
      closeOnSelect: true,
    });

  return commands;
};
