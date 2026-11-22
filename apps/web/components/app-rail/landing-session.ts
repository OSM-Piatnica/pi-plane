/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observable, runInAction } from "mobx";
import type { TAppRailLandingStep } from "@plane/utils";

/** How long the workspace root may stay blank while the landing is being decided or carried out */
export const APP_RAIL_LANDING_TIMEOUT_MS = 3000;

/**
 * Identifies one entry into a workspace by one user. The landing is decided once per session
 * key, so a different user signing in in the same tab (no reload) gets their own landing.
 * Undefined while the user or the workspace is unknown: nothing is decided then.
 */
export const getAppRailLandingSessionKey = (
  userId: string | undefined,
  workspaceSlug: string | undefined
): string | undefined => (userId && workspaceSlug ? `${userId}:${workspaceSlug}` : undefined);

export type TAppRailLandingSession = {
  /** The session whose landing has been decided */
  settledKey: string | undefined;
  /** Where the landing sent the user, until the route has left the workspace root */
  redirectTo: string | undefined;
};

/**
 * The landing state of the tab. It outlives the component on purpose: going back to the
 * workspace root later (the Projects rail item leads there) is not a new entry.
 */
export const createAppRailLandingSession = () => {
  const state = observable<TAppRailLandingSession>({ settledKey: undefined, redirectTo: undefined });
  return {
    state,
    settle: (sessionKey: string, redirectTo: string | undefined) =>
      runInAction(() => {
        state.settledKey = sessionKey;
        state.redirectTo = redirectTo;
      }),
  };
};

export type TAppRailLandingSessionStore = ReturnType<typeof createAppRailLandingSession>;

export type TAppRailLandingViewInput = {
  session: TAppRailLandingSession;
  sessionKey: string | undefined;
  isAtRoot: boolean;
  hasMultipleApps: boolean;
  activeAppKey: string | undefined;
  /** Decides the landing; only called while the session is not settled */
  resolve: () => TAppRailLandingStep;
};

export type TAppRailLandingView = {
  /** Render nothing: the root would only flash before the user is sent elsewhere */
  isHidden: boolean;
  /** Effect 1: the decision is ready; settle the session and go to `redirectTo` if set */
  settle: { redirectTo: string | undefined } | undefined;
  /** Effect 2: the redirect has arrived (or the user went elsewhere); the root may render again */
  clearRedirect: boolean;
  /** Effect 3: while hidden, settle without a redirect after `APP_RAIL_LANDING_TIMEOUT_MS` */
  needsFallbackTimeout: boolean;
  /** Effect 4: the app to remember as last used, once the landing is over */
  lastUsedAppToRecord: string | undefined;
};

/**
 * What `AppRailLanding` renders and which of its effects act, for one render. The effects run
 * in the order of the fields: settle, clear the redirect, the fallback timeout, the last used app.
 */
export const getAppRailLandingView = ({
  session,
  sessionKey,
  isAtRoot,
  hasMultipleApps,
  activeAppKey,
  resolve,
}: TAppRailLandingViewInput): TAppRailLandingView => {
  const isSettled = sessionKey !== undefined && session.settledKey === sessionKey;
  const redirectInFlight = isSettled ? session.redirectTo : undefined;
  // nothing is decided while the user or the workspace is unknown
  const step = sessionKey && !isSettled ? resolve() : undefined;
  const decided = step && !step.isPending ? step : undefined;
  const isHidden = isAtRoot && (step?.isPending === true || Boolean(decided?.redirectTo) || Boolean(redirectInFlight));

  return {
    isHidden,
    settle: sessionKey && decided ? { redirectTo: decided.redirectTo } : undefined,
    clearRedirect: Boolean(sessionKey && redirectInFlight && !isAtRoot),
    needsFallbackTimeout: Boolean(sessionKey && isHidden),
    lastUsedAppToRecord:
      sessionKey && isSettled && !redirectInFlight && hasMultipleApps && !isHidden ? activeAppKey : undefined,
  };
};

/** Starts the fallback that opens the root after the timeout; returns the cleanup */
export const startAppRailLandingFallback = (
  onTimeout: () => void,
  timers: { set: typeof setTimeout; clear: typeof clearTimeout } = { set: setTimeout, clear: clearTimeout }
): (() => void) => {
  const timeout = timers.set(onTimeout, APP_RAIL_LANDING_TIMEOUT_MS);
  return () => timers.clear(timeout);
};
