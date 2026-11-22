/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserWorkspaceRoles } from "@plane/types";

export type TWorkspaceFeaturesPageAccess = "loading" | "denied" | "allowed";

/**
 * Who may open the Features settings page: workspace admins. The role is undefined until the
 * user's membership of the workspace has loaded; the page waits then instead of briefly saying
 * "not authorised" to an admin.
 */
export const getWorkspaceFeaturesPageAccess = (role: number | undefined): TWorkspaceFeaturesPageAccess => {
  if (role === undefined) return "loading";
  return role === EUserWorkspaceRoles.ADMIN ? "allowed" : "denied";
};
