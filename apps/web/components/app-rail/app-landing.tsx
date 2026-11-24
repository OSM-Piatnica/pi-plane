/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useParams, usePathname } from "next/navigation";
import { isWorkspaceRootPath, resolveAppRailLanding } from "@plane/utils";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import {
  createAppRailLandingSession,
  getAppRailLandingSessionKey,
  getAppRailLandingView,
  startAppRailLandingFallback,
} from "./landing-session";
import { readLastUsedApp, writeLastUsedApp } from "./last-used-app";
import { useAppRailApps } from "./use-app-rail-apps";

/**
 * The landing is decided once per entry of a user into a workspace: on page load, after sign-in,
 * when switching workspaces, and when another user signs in in the same tab. It outlives the
 * component on purpose, so that going back to the workspace root later is not a new entry.
 */
const landingSession = createAppRailLandingSession();

type Props = {
  children: ReactNode;
};

/**
 * Sends a user who enters a workspace at its root to their app: the default app they chose,
 * else the app they last used here, else the root as before. A deep link is never redirected.
 * It also remembers the last used app. See "Default app and landing" in `docs/app-rail.md`.
 * The decisions are in `landing-session.ts`; this component only carries them out.
 *
 * With a single enabled app it decides at once and renders its children untouched.
 */
export const AppRailLanding = observer(function AppRailLanding({ children }: Props) {
  const { workspaceSlug: routeWorkspaceSlug } = useParams();
  const pathname = usePathname();
  const router = useAppRouter();
  const { data: currentUser } = useUser();
  const { enabledApps, activeAppKey, hasMultipleApps } = useAppRailApps();
  const { getProjectNavigationPreferences } = useWorkspace();

  const workspaceSlug = routeWorkspaceSlug?.toString();
  const sessionKey = getAppRailLandingSessionKey(currentUser?.id, workspaceSlug);
  // the user's workspace properties carry `default_app`; undefined until they have loaded
  const properties = workspaceSlug ? getProjectNavigationPreferences(workspaceSlug) : undefined;

  const view = getAppRailLandingView({
    session: landingSession.state,
    sessionKey,
    isAtRoot: isWorkspaceRootPath(pathname, workspaceSlug),
    hasMultipleApps,
    activeAppKey,
    resolve: () =>
      resolveAppRailLanding({
        enabledApps,
        pathname,
        workspaceSlug,
        defaultAppKey: properties?.default_app,
        lastUsedAppKey: hasMultipleApps && workspaceSlug ? readLastUsedApp(workspaceSlug) : undefined,
        isDefaultAppKnown: properties !== undefined,
      }),
  });
  const isReadyToSettle = view.settle !== undefined;
  const settleRedirectTo = view.settle?.redirectTo;

  useEffect(() => {
    if (!sessionKey || !isReadyToSettle) return;
    landingSession.settle(sessionKey, settleRedirectTo);
    if (settleRedirectTo) router.replace(settleRedirectTo);
  }, [sessionKey, isReadyToSettle, settleRedirectTo, router]);

  useEffect(() => {
    if (sessionKey && view.clearRedirect) landingSession.settle(sessionKey, undefined);
  }, [sessionKey, view.clearRedirect]);

  useEffect(() => {
    if (!sessionKey || !view.needsFallbackTimeout) return;
    return startAppRailLandingFallback(() => landingSession.settle(sessionKey, undefined));
  }, [sessionKey, view.needsFallbackTimeout]);

  useEffect(() => {
    if (workspaceSlug && view.lastUsedAppToRecord) writeLastUsedApp(workspaceSlug, view.lastUsedAppToRecord);
  }, [workspaceSlug, view.lastUsedAppToRecord]);

  return view.isHidden ? null : <>{children}</>;
});
