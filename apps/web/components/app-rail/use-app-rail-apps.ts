/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams, usePathname } from "next/navigation";
import type { EUserWorkspaceRoles, TAppRailAppKey, TAppRailContext } from "@plane/types";
import { getAppRailState, getWorkspaceFeatureFlags } from "@plane/utils";
import type { TAppRailState } from "@plane/utils";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { APP_RAIL_APPS } from "./registry";

/**
 * Reads the rail registry for the current workspace, user and route.
 * Call it from an `observer` component: the context comes from MobX stores.
 */
export const useAppRailApps = (): TAppRailState<TAppRailAppKey> => {
  const { workspaceSlug: routeWorkspaceSlug } = useParams();
  const pathname = usePathname();
  const { currentWorkspace, getNavigationPreferences } = useWorkspace();
  const { data: currentUser } = useUser();
  const { getWorkspaceRoleByWorkspaceSlug } = useUserPermissions();

  const workspaceSlug = routeWorkspaceSlug?.toString();
  const context: TAppRailContext = {
    workspaceSlug,
    workspace: currentWorkspace ?? undefined,
    user: currentUser,
    workspaceRole: workspaceSlug
      ? (getWorkspaceRoleByWorkspaceSlug(workspaceSlug) as EUserWorkspaceRoles | undefined)
      : undefined,
    // the switches arrive with the workspace itself, so they are known as soon as it is
    features: getWorkspaceFeatureFlags(currentWorkspace?.enabled_features),
  };
  // the user's order and hidden apps; until they load the rail is in registry order
  const preferences = workspaceSlug ? getNavigationPreferences(workspaceSlug) : undefined;

  return getAppRailState(APP_RAIL_APPS, context, pathname, preferences);
};
