/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import type { TAppRailLandingStep } from "@plane/utils";
import {
  APP_RAIL_LANDING_TIMEOUT_MS,
  createAppRailLandingSession,
  getAppRailLandingSessionKey,
  getAppRailLandingView,
  startAppRailLandingFallback,
} from "@/components/app-rail/landing-session";
import type { TAppRailLandingViewInput } from "@/components/app-rail/landing-session";

const PENDING: TAppRailLandingStep = { isPending: true };
const decided = (redirectTo?: string): TAppRailLandingStep => ({ isPending: false, redirectTo });

const viewOf = (overrides: Partial<TAppRailLandingViewInput> & Pick<TAppRailLandingViewInput, "session">) =>
  getAppRailLandingView({
    sessionKey: "u1:acme",
    isAtRoot: true,
    hasMultipleApps: true,
    activeAppKey: "projects",
    resolve: () => decided(),
    ...overrides,
  });

describe("getAppRailLandingSessionKey", () => {
  it("is per user and workspace", () => {
    expect(getAppRailLandingSessionKey("u1", "acme")).toBe("u1:acme");
    expect(getAppRailLandingSessionKey("u2", "acme")).not.toBe(getAppRailLandingSessionKey("u1", "acme"));
    expect(getAppRailLandingSessionKey("u1", "other")).not.toBe(getAppRailLandingSessionKey("u1", "acme"));
  });

  it("is undefined while the user or the workspace is unknown", () => {
    expect(getAppRailLandingSessionKey(undefined, "acme")).toBeUndefined();
    expect(getAppRailLandingSessionKey("u1", undefined)).toBeUndefined();
  });
});

describe("the landing of one entry, render by render", () => {
  it("waits, redirects, clears the redirect, then records the last used app", () => {
    const session = createAppRailLandingSession();
    const resolve = vi.fn(() => PENDING);

    // 1. properties still loading: hidden, nothing settled, fallback armed
    let view = viewOf({ session: session.state, resolve });
    expect(view).toEqual({
      isHidden: true,
      settle: undefined,
      clearRedirect: false,
      needsFallbackTimeout: true,
      lastUsedAppToRecord: undefined,
    });

    // 2. decided with a redirect: still hidden, effect 1 settles
    view = viewOf({ session: session.state, resolve: () => decided("/acme/wiki/") });
    expect(view.isHidden).toBe(true);
    expect(view.settle).toEqual({ redirectTo: "/acme/wiki/" });
    expect(view.lastUsedAppToRecord).toBeUndefined();
    session.settle("u1:acme", "/acme/wiki/");

    // 3. settled, router not yet moved: hidden, the decision is not taken again
    resolve.mockClear();
    view = viewOf({ session: session.state, resolve });
    expect(resolve).not.toHaveBeenCalled();
    expect(view.isHidden).toBe(true);
    expect(view.settle).toBeUndefined();
    expect(view.clearRedirect).toBe(false);
    expect(view.lastUsedAppToRecord).toBeUndefined();

    // 4. the route has arrived in the app: effect 2 clears the redirect, nothing recorded yet
    view = viewOf({ session: session.state, isAtRoot: false, activeAppKey: "wiki" });
    expect(view.isHidden).toBe(false);
    expect(view.clearRedirect).toBe(true);
    expect(view.lastUsedAppToRecord).toBeUndefined();
    session.settle("u1:acme", undefined);

    // 5. landing over: the app in use is recorded
    view = viewOf({ session: session.state, isAtRoot: false, activeAppKey: "wiki" });
    expect(view.clearRedirect).toBe(false);
    expect(view.lastUsedAppToRecord).toBe("wiki");

    // 6. back at the root later: not a new entry, shown as it is
    view = viewOf({ session: session.state, resolve: () => decided("/acme/wiki/") });
    expect(view.isHidden).toBe(false);
    expect(view.settle).toBeUndefined();
  });

  it("settles without a redirect when the user stays at the root", () => {
    const session = createAppRailLandingSession();
    const view = viewOf({ session: session.state });
    expect(view.isHidden).toBe(false);
    expect(view.settle).toEqual({ redirectTo: undefined });
    expect(view.needsFallbackTimeout).toBe(false);
  });

  it("never hides a deep link", () => {
    const session = createAppRailLandingSession();
    const view = viewOf({ session: session.state, isAtRoot: false, resolve: () => PENDING });
    expect(view.isHidden).toBe(false);
    expect(view.needsFallbackTimeout).toBe(false);
  });

  it("does nothing and records nothing while the user is unknown", () => {
    const session = createAppRailLandingSession();
    session.settle("u1:acme", "/acme/wiki/");
    const resolve = vi.fn(() => PENDING);
    const view = viewOf({ session: session.state, sessionKey: undefined, resolve });
    expect(resolve).not.toHaveBeenCalled();
    expect(view).toEqual({
      isHidden: false,
      settle: undefined,
      clearRedirect: false,
      needsFallbackTimeout: false,
      lastUsedAppToRecord: undefined,
    });
  });

  it("gives another user signing in in the same tab their own landing", () => {
    const session = createAppRailLandingSession();
    session.settle("u1:acme", undefined);
    expect(viewOf({ session: session.state, sessionKey: "u1:acme" }).settle).toBeUndefined();

    const view = viewOf({ session: session.state, sessionKey: "u2:acme", resolve: () => decided("/acme/wiki/") });
    expect(view.settle).toEqual({ redirectTo: "/acme/wiki/" });
    expect(view.isHidden).toBe(true);
  });

  it("does not let another session's redirect hide the root", () => {
    const session = createAppRailLandingSession();
    session.settle("u1:acme", "/acme/wiki/");
    expect(viewOf({ session: session.state, sessionKey: "u1:other" }).isHidden).toBe(false);
  });

  it("records nothing with a single app", () => {
    const session = createAppRailLandingSession();
    session.settle("u1:acme", undefined);
    expect(viewOf({ session: session.state, hasMultipleApps: false }).lastUsedAppToRecord).toBeUndefined();
  });
});

describe("startAppRailLandingFallback", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("opens the root after the timeout", () => {
    vi.useFakeTimers();
    const session = createAppRailLandingSession();
    startAppRailLandingFallback(() => session.settle("u1:acme", undefined));

    vi.advanceTimersByTime(APP_RAIL_LANDING_TIMEOUT_MS - 1);
    expect(viewOf({ session: session.state, resolve: () => PENDING }).isHidden).toBe(true);

    vi.advanceTimersByTime(1);
    expect(session.state.settledKey).toBe("u1:acme");
    expect(viewOf({ session: session.state, resolve: () => PENDING }).isHidden).toBe(false);
  });

  it("is cancelled by its cleanup", () => {
    vi.useFakeTimers();
    const onTimeout = vi.fn();
    const stop = startAppRailLandingFallback(onTimeout);
    stop();
    vi.advanceTimersByTime(APP_RAIL_LANDING_TIMEOUT_MS * 2);
    expect(onTimeout).not.toHaveBeenCalled();
  });

  it("waits three seconds", () => {
    expect(APP_RAIL_LANDING_TIMEOUT_MS).toBe(3000);
  });
});
