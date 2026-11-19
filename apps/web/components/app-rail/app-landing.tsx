/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import type { ReactNode } from "react";
import { observable, runInAction } from "mobx";
import { observer } from "mobx-react";
import { useParams, usePathname } from "next/navigation";
import { isWorkspaceRootPath, resolveAppRailLanding } from "@plane/utils";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useAppRouter } from "@/hooks/use-app-router";
import { readLastUsedApp, writeLastUsedApp } from "./last-used-app";
import { useAppRailApps } from "./use-app-rail-apps";

/** How long the workspace root may stay blank while the landing is being decided or carried out */
const LANDING_TIMEOUT_MS = 3000;

/**
 * The landing is decided once per entry into a workspace: on page load, after sign-in, and when
 * switching workspaces. It is module state on purpose, so that going back to the workspace root
 * later (the Projects rail item leads there) is not taken for a new entry.
 */
const landingState = observable({
  /** The workspace whose landing has been decided */
  workspaceSlug: undefined as string | undefined,
  /** Where the landing sends the user, until the route has left the workspace root */
  redirectTo: undefined as string | undefined,
});

const settleLanding = (workspaceSlug: string, redirectTo: string | undefined) =>
  runInAction(() => {
    landingState.workspaceSlug = workspaceSlug;
    landingState.redirectTo = redirectTo;
  });

type Props = {
  children: ReactNode;
};

/**
 * Sends a user who enters a workspace at its root to their app: the default app they chose,
 * else the app they last used here, else the root as before. A deep link is never redirected.
 * It also remembers the last used app. See "Default app and landing" in `docs/app-rail.md`.
 *
 * With a single enabled app it decides at once and renders its children untouched.
 */
export const AppRailLanding = observer(function AppRailLanding({ children }: Props) {
  const { workspaceSlug: routeWorkspaceSlug } = useParams();
  const pathname = usePathname();
  const router = useAppRouter();
  const { enabledApps, activeAppKey, hasMultipleApps } = useAppRailApps();
  const { getProjectNavigationPreferences } = useWorkspace();

  const workspaceSlug = routeWorkspaceSlug?.toString();
  // the user's workspace properties carry `default_app`; undefined until they have loaded
  const properties = workspaceSlug ? getProjectNavigationPreferences(workspaceSlug) : undefined;
  const isAtRoot = isWorkspaceRootPath(pathname, workspaceSlug);
  const isDecided = !workspaceSlug || landingState.workspaceSlug === workspaceSlug;
  const redirectInFlight = isDecided ? landingState.redirectTo : undefined;

  const step = isDecided
    ? undefined
    : resolveAppRailLanding({
        enabledApps,
        pathname,
        workspaceSlug,
        defaultAppKey: properties?.default_app,
        lastUsedAppKey: hasMultipleApps && workspaceSlug ? readLastUsedApp(workspaceSlug) : undefined,
        isDefaultAppKnown: properties !== undefined,
      });
  const isReady = step !== undefined && !step.isPending;
  const redirectTo = step !== undefined && !step.isPending ? step.redirectTo : undefined;
  // the root stays blank while its content would only flash before the user is sent elsewhere
  const isHidden = isAtRoot && (step?.isPending === true || Boolean(redirectTo) || Boolean(redirectInFlight));

  useEffect(() => {
    if (!workspaceSlug || !isReady) return;
    settleLanding(workspaceSlug, redirectTo);
    if (redirectTo) router.replace(redirectTo);
  }, [workspaceSlug, isReady, redirectTo, router]);

  // the redirect has arrived (or the user went elsewhere): the root may render again from now on
  useEffect(() => {
    if (workspaceSlug && redirectInFlight && !isAtRoot) settleLanding(workspaceSlug, undefined);
  }, [workspaceSlug, redirectInFlight, isAtRoot]);

  // never leave the root blank: if the preference does not load or the redirect does not happen,
  // the root opens as it always did
  useEffect(() => {
    if (!workspaceSlug || !isHidden) return;
    const timeout = setTimeout(() => settleLanding(workspaceSlug, undefined), LANDING_TIMEOUT_MS);
    return () => clearTimeout(timeout);
  }, [workspaceSlug, isHidden]);

  // remember the app in use, once the landing is over so it cannot overwrite what it reads
  useEffect(() => {
    if (!workspaceSlug || !hasMultipleApps || !activeAppKey || isHidden) return;
    if (landingState.workspaceSlug !== workspaceSlug || landingState.redirectTo) return;
    writeLastUsedApp(workspaceSlug, activeAppKey);
  }, [workspaceSlug, hasMultipleApps, activeAppKey, isHidden]);

  return isHidden ? null : <>{children}</>;
});
