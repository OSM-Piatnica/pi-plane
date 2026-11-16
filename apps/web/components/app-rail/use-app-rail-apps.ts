/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams, usePathname } from "next/navigation";
import type { EUserWorkspaceRoles, TAppRailApp, TAppRailAppKey, TAppRailContext } from "@plane/types";
import { getActiveAppRailAppKey, getEnabledAppRailApps, hasMultipleAppRailApps } from "@plane/utils";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { APP_RAIL_APPS } from "./registry";

type TUseAppRailApps = {
  /** Apps offered to the current user in the current workspace, in rail order */
  enabledApps: TAppRailApp[];
  /** The enabled app the current route belongs to */
  activeAppKey: TAppRailAppKey | undefined;
  /** False with a single enabled app: no rail, no switch commands, no shortcuts */
  hasMultipleApps: boolean;
};

/**
 * Reads the rail registry for the current workspace, user and route.
 * Call it from an `observer` component: the context comes from MobX stores.
 */
export const useAppRailApps = (): TUseAppRailApps => {
  const { workspaceSlug: routeWorkspaceSlug } = useParams();
  const pathname = usePathname();
  const { currentWorkspace } = useWorkspace();
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
  };
  const enabledApps = getEnabledAppRailApps(APP_RAIL_APPS, context);

  return {
    enabledApps,
    activeAppKey: getActiveAppRailAppKey(enabledApps, pathname, workspaceSlug),
    hasMultipleApps: hasMultipleAppRailApps(enabledApps),
  };
};
