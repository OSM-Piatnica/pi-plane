/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IUser } from "./users";
import type { EUserWorkspaceRoles, IWorkspace } from "./workspace";

/**
 * Keys of the apps that can appear in the app rail. Adding an app starts here: the registry
 * and the icon map are keyed by this union, so the compiler lists what is missing.
 * See `docs/app-rail.md`.
 */
export type TAppRailAppKey = "projects";

/** What an app's `isEnabled` predicate may look at. Every field can be missing while data loads. */
export type TAppRailContext = {
  workspaceSlug: string | undefined;
  workspace: IWorkspace | undefined;
  user: IUser | undefined;
  workspaceRole: EUserWorkspaceRoles | undefined;
};

/**
 * One app of the rail, without its React parts (icon, sidebar), so it can be used and tested
 * outside the browser.
 */
export type TAppRailApp<TKey extends string = TAppRailAppKey> = {
  key: TKey;
  /** i18n key of the label under the rail icon */
  i18n_label: string;
  /** i18n key of the command palette entry that switches to the app ("Switch to Projects") */
  i18n_switch_label: string;
  /**
   * First path segments after the workspace slug that belong to the app, for example
   * `["approvals"]` for `/:workspaceSlug/approvals/...`. The default app owns every other path.
   */
  routeSegments: readonly string[];
  /** Exactly one app is the default: it owns every workspace path no other app claims */
  isDefault?: boolean;
  /** Where the rail item and the switch command lead */
  getHref: (workspaceSlug: string) => string;
  /** Whether the app is offered to this user in this workspace */
  isEnabled: (context: TAppRailContext) => boolean;
};
