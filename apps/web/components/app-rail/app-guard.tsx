/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import type { TAppRailAppKey } from "@plane/types";
import { getAppRailRouteAccess } from "@plane/utils";
import { useAppRouter } from "@/hooks/use-app-router";
import { useAppRailApps } from "./use-app-rail-apps";

type Props = {
  appKey: TAppRailAppKey;
  children: ReactNode;
};

/**
 * Wraps the layout of a rail app's route group. When the app is not enabled for the current
 * user in this workspace, its routes do not render and the user is sent to the default app.
 *
 * The workspace layout renders its children only after the workspace and the membership have
 * loaded, so `isEnabled` sees a complete context here.
 */
export const AppRailAppGuard = observer(function AppRailAppGuard({ appKey, children }: Props) {
  const { workspaceSlug } = useParams();
  const router = useAppRouter();
  const { enabledApps } = useAppRailApps();

  const access = getAppRailRouteAccess(enabledApps, appKey, workspaceSlug?.toString());
  const redirectTo = access.isAllowed ? undefined : access.redirectTo;

  useEffect(() => {
    if (redirectTo) router.replace(redirectTo);
  }, [redirectTo, router]);

  return access.isAllowed ? <>{children}</> : null;
});
