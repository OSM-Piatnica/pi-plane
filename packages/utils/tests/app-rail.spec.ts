/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAppRailApp, TAppRailContext } from "@plane/types";
import {
  arrangeAppRailApps,
  buildAppRailPreferenceUpdate,
  canHideAppRailApp,
  getActiveAppRailAppKey,
  getAppRailDefaultAppKey,
  getAppRailDockItems,
  getAppRailLandingApp,
  getAppRailLandingRedirect,
  getAppRailPreferenceKey,
  getAppRailRouteAccess,
  getAppRailState,
  getAppRailSwitchKeySequence,
  getEnabledAppRailApps,
  hasMultipleAppRailApps,
  isWorkspaceRootPath,
  resolveAppRailLanding,
  validateAppRailApps,
} from "../src/app-rail";
import { getWorkspaceFeatureFlags } from "../src/workspace-features";

type TKey = "projects" | "approvals" | "wiki";

const app = (key: TKey, overrides: Partial<TAppRailApp<TKey>> = {}): TAppRailApp<TKey> => ({
  key,
  i18n_label: key,
  i18n_switch_label: `app_rail.switch_to.${key}`,
  routeSegments: [key],
  getHref: (workspaceSlug) => `/${workspaceSlug}/${key}/`,
  isEnabled: () => true,
  ...overrides,
});

const projects = app("projects", { routeSegments: [], isDefault: true, getHref: (slug) => `/${slug}/` });
const approvals = app("approvals");
const wiki = app("wiki", { routeSegments: ["wiki", "pages"] });
const APPS = [projects, approvals, wiki];

const context = (overrides: Partial<TAppRailContext> = {}): TAppRailContext => ({
  workspaceSlug: "acme",
  workspace: undefined,
  user: undefined,
  workspaceRole: undefined,
  features: getWorkspaceFeatureFlags(undefined),
  ...overrides,
});

describe("getEnabledAppRailApps", () => {
  it("keeps registry order", () => {
    expect(getEnabledAppRailApps(APPS, context()).map((a) => a.key)).toEqual(["projects", "approvals", "wiki"]);
    expect(getEnabledAppRailApps([wiki, projects, approvals], context()).map((a) => a.key)).toEqual([
      "wiki",
      "projects",
      "approvals",
    ]);
  });

  it("drops apps whose predicate rejects the context", () => {
    const apps = [projects, app("approvals", { isEnabled: () => false }), wiki];
    expect(getEnabledAppRailApps(apps, context()).map((a) => a.key)).toEqual(["projects", "wiki"]);
  });

  it("hands the context to the predicate", () => {
    const apps = [projects, app("wiki", { isEnabled: (ctx) => ctx.workspaceSlug === "acme" })];
    expect(getEnabledAppRailApps(apps, context()).map((a) => a.key)).toEqual(["projects", "wiki"]);
    expect(getEnabledAppRailApps(apps, context({ workspaceSlug: "other" })).map((a) => a.key)).toEqual(["projects"]);
  });
});

describe("hasMultipleAppRailApps", () => {
  it("is false with no app or a single app", () => {
    expect(hasMultipleAppRailApps([])).toBe(false);
    expect(hasMultipleAppRailApps([projects])).toBe(false);
  });

  it("is true from two apps", () => {
    expect(hasMultipleAppRailApps([projects, approvals])).toBe(true);
  });
});

describe("getActiveAppRailAppKey", () => {
  it("gives the default app the workspace home and every unclaimed path", () => {
    expect(getActiveAppRailAppKey(APPS, "/acme", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(APPS, "/acme/", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(APPS, "/acme/projects/p1/issues/", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(APPS, "/acme/analytics/overview", "acme")).toBe("projects");
  });

  it("gives an app the paths under its route segments", () => {
    expect(getActiveAppRailAppKey(APPS, "/acme/approvals", "acme")).toBe("approvals");
    expect(getActiveAppRailAppKey(APPS, "/acme/approvals/waiting/", "acme")).toBe("approvals");
    expect(getActiveAppRailAppKey(APPS, "/acme/wiki/page-1", "acme")).toBe("wiki");
    expect(getActiveAppRailAppKey(APPS, "/acme/pages/", "acme")).toBe("wiki");
  });

  it("compares whole segments", () => {
    expect(getActiveAppRailAppKey(APPS, "/acme/approvals-archive", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(APPS, "/acme/projects/p1/approvals", "acme")).toBe("projects");
  });

  it("ignores query string and hash", () => {
    expect(getActiveAppRailAppKey(APPS, "/acme/approvals?tab=sent", "acme")).toBe("approvals");
    expect(getActiveAppRailAppKey(APPS, "/acme/wiki#top", "acme")).toBe("wiki");
  });

  it("highlights no app on settings and notifications", () => {
    expect(getActiveAppRailAppKey(APPS, "/acme/settings", "acme")).toBeUndefined();
    expect(getActiveAppRailAppKey(APPS, "/acme/settings/members/", "acme")).toBeUndefined();
    expect(getActiveAppRailAppKey(APPS, "/acme/notifications/", "acme")).toBeUndefined();
  });

  it("keeps project settings in the default app", () => {
    expect(getActiveAppRailAppKey(APPS, "/acme/projects/p1/settings/", "acme")).toBe("projects");
  });

  it("falls back to the default app when the app of the path is not enabled", () => {
    expect(getActiveAppRailAppKey([projects, wiki], "/acme/approvals/", "acme")).toBe("projects");
  });

  it("gives the default app the workspace routes without a slug in the URL", () => {
    expect(getActiveAppRailAppKey(APPS, "/i/ACME-12", "acme")).toBe("projects");
  });

  it("returns nothing without a workspace or without a default app", () => {
    expect(getActiveAppRailAppKey(APPS, "/acme/approvals", undefined)).toBeUndefined();
    expect(getActiveAppRailAppKey([approvals], "/acme/projects", "acme")).toBeUndefined();
  });

  it("with a single app behaves like the former hard-coded Projects item", () => {
    const single = [projects];
    expect(getActiveAppRailAppKey(single, "/acme/", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(single, "/acme/projects/", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(single, "/acme/notifications/", "acme")).toBeUndefined();
    expect(getActiveAppRailAppKey(single, "/acme/settings/", "acme")).toBeUndefined();
  });
});

describe("getAppRailSwitchKeySequence", () => {
  it("numbers the first nine apps from g1", () => {
    expect(getAppRailSwitchKeySequence(0)).toBe("g1");
    expect(getAppRailSwitchKeySequence(8)).toBe("g9");
  });

  it("gives no shortcut beyond the ninth app or for an invalid position", () => {
    expect(getAppRailSwitchKeySequence(9)).toBeUndefined();
    expect(getAppRailSwitchKeySequence(-1)).toBeUndefined();
  });
});

describe("validateAppRailApps", () => {
  it("accepts a consistent registry", () => {
    expect(validateAppRailApps(APPS)).toEqual([]);
    expect(validateAppRailApps([projects])).toEqual([]);
  });

  it("requires exactly one default app", () => {
    expect(validateAppRailApps([approvals])).toEqual(["expected exactly one default app, found 0"]);
    expect(validateAppRailApps([projects, app("wiki", { isDefault: true })])).toEqual([
      "expected exactly one default app, found 2",
    ]);
  });

  it("reports duplicate keys and route segments claimed twice", () => {
    expect(validateAppRailApps([projects, approvals, approvals])).toEqual([
      'duplicate app key "approvals"',
      'route segment "approvals" is claimed by "approvals" and "approvals"',
    ]);
    expect(validateAppRailApps([projects, approvals, app("wiki", { routeSegments: ["approvals"] })])).toEqual([
      'route segment "approvals" is claimed by "approvals" and "wiki"',
    ]);
  });

  it("reports reserved segments and apps that own no path", () => {
    expect(validateAppRailApps([projects, app("wiki", { routeSegments: ["settings"] })])).toEqual([
      'app "wiki" claims the reserved route segment "settings"',
    ]);
    expect(validateAppRailApps([projects, app("wiki", { routeSegments: [] })])).toEqual([
      'app "wiki" owns no route segment and is not the default app',
    ]);
  });
});

describe("getAppRailState", () => {
  it("derives enabled apps, the active app and the multi-app flag in one go", () => {
    const apps = [projects, app("approvals", { isEnabled: (ctx) => ctx.workspaceSlug === "acme" }), wiki];
    const state = getAppRailState(apps, context(), "/acme/approvals/waiting");
    expect(state.enabledApps.map((a) => a.key)).toEqual(["projects", "approvals", "wiki"]);
    expect(state.activeAppKey).toBe("approvals");
    expect(state.hasMultipleApps).toBe(true);
  });

  it("resolves the active app among the enabled apps only", () => {
    const apps = [projects, app("approvals", { isEnabled: () => false })];
    const state = getAppRailState(apps, context(), "/acme/approvals/");
    expect(state.enabledApps.map((a) => a.key)).toEqual(["projects"]);
    expect(state.activeAppKey).toBe("projects");
    expect(state.hasMultipleApps).toBe(false);
  });

  it("has no active app while the workspace is unknown", () => {
    const state = getAppRailState(APPS, context({ workspaceSlug: undefined }), "/acme/");
    expect(state.activeAppKey).toBeUndefined();
  });
});

describe("getAppRailDockItems", () => {
  it("lists one item per enabled app in rail order and marks the active one", () => {
    const state = getAppRailState(APPS, context(), "/acme/wiki/");
    expect(getAppRailDockItems(state, "acme")).toEqual([
      { key: "projects", i18n_label: "projects", href: "/acme/", isActive: false },
      { key: "approvals", i18n_label: "approvals", href: "/acme/approvals/", isActive: false },
      { key: "wiki", i18n_label: "wiki", href: "/acme/wiki/", isActive: true },
    ]);
  });

  it("marks no item on settings and notifications", () => {
    const state = getAppRailState(APPS, context(), "/acme/settings/members");
    expect(getAppRailDockItems(state, "acme").some((item) => item.isActive)).toBe(false);
  });

  it("gives every item a distinct key even when labels repeat", () => {
    const apps = [projects, app("approvals", { i18n_label: "projects" })];
    const items = getAppRailDockItems(getAppRailState(apps, context(), "/acme/"), "acme");
    expect(new Set(items.map((item) => item.key)).size).toBe(items.length);
  });
});

describe("getAppRailRouteAccess", () => {
  it("allows the routes of an enabled app", () => {
    expect(getAppRailRouteAccess(APPS, "approvals", "acme")).toEqual({ isAllowed: true });
    expect(getAppRailRouteAccess([projects], "projects", "acme")).toEqual({ isAllowed: true });
  });

  it("sends the user of a disabled app to the default app", () => {
    expect(getAppRailRouteAccess([wiki, projects], "approvals", "acme")).toEqual({
      isAllowed: false,
      redirectTo: "/acme/",
    });
  });

  it("falls back to the first enabled app when the default app is not enabled", () => {
    expect(getAppRailRouteAccess([wiki, approvals], "projects", "acme")).toEqual({
      isAllowed: false,
      redirectTo: "/acme/wiki/",
    });
  });

  it("blocks without a target when there is no workspace or no enabled app", () => {
    expect(getAppRailRouteAccess([projects], "approvals", undefined)).toEqual({
      isAllowed: false,
      redirectTo: undefined,
    });
    expect(getAppRailRouteAccess([], "approvals", "acme")).toEqual({ isAllowed: false, redirectTo: undefined });
  });
});

describe("isEnabled with workspace feature switches", () => {
  // what a feature-gated app will declare once its feature is available
  const gated = [projects, app("approvals", { isEnabled: ({ features }) => features.approvals }), wiki];

  it("hands every feature flag to the predicate, all off by default", () => {
    expect(context().features).toEqual({ lite: false, approvals: false, initiatives: false, wiki: false, raci: false });
    expect(getEnabledAppRailApps(gated, context()).map((a) => a.key)).toEqual(["projects", "wiki"]);
  });

  it("offers the app once the workspace switches its feature on", () => {
    const features = { ...context().features, approvals: true };
    expect(getEnabledAppRailApps(gated, context({ features })).map((a) => a.key)).toEqual([
      "projects",
      "approvals",
      "wiki",
    ]);
  });

  it("closes the app's routes while the feature is off", () => {
    const enabled = getEnabledAppRailApps(gated, context());
    expect(getAppRailRouteAccess(enabled, "approvals", "acme")).toEqual({ isAllowed: false, redirectTo: "/acme/" });
  });
});

const keys = (apps: readonly TAppRailApp<TKey>[]) => apps.map((a) => a.key);
const pref = (key: TKey, is_pinned: boolean, sort_order?: number) => ({
  [getAppRailPreferenceKey(key)]: { is_pinned, sort_order },
});

describe("arrangeAppRailApps", () => {
  it("uses the prefix the API accepts", () => {
    expect(getAppRailPreferenceKey("approvals")).toBe("app_rail:approvals");
  });

  it("keeps registry order with nothing hidden when there are no preferences", () => {
    for (const preferences of [undefined, null, {}]) {
      const arrangement = arrangeAppRailApps(APPS, preferences);
      expect(keys(arrangement.railApps)).toEqual(["projects", "approvals", "wiki"]);
      expect(keys(arrangement.orderedApps)).toEqual(["projects", "approvals", "wiki"]);
      expect(arrangement.items.every((item) => !item.isHidden)).toBe(true);
    }
  });

  it("ignores the sidebar preferences that are not about apps", () => {
    const preferences = { drafts: { is_pinned: false, sort_order: 0 }, approvals: { is_pinned: false, sort_order: 0 } };
    expect(keys(arrangeAppRailApps(APPS, preferences).railApps)).toEqual(["projects", "approvals", "wiki"]);
  });

  it("orders by the stored position", () => {
    const preferences = { ...pref("projects", true, 2), ...pref("approvals", true, 1), ...pref("wiki", true, 0) };
    expect(keys(arrangeAppRailApps(APPS, preferences).railApps)).toEqual(["wiki", "approvals", "projects"]);
  });

  it("puts apps without a stored position after the others, in registry order", () => {
    // wiki was moved first before approvals existed for this user
    const preferences = { ...pref("wiki", true, 0) };
    expect(keys(arrangeAppRailApps(APPS, preferences).railApps)).toEqual(["wiki", "projects", "approvals"]);
  });

  it("breaks equal positions by registry order", () => {
    const preferences = { ...pref("wiki", true, 5), ...pref("projects", true, 5), ...pref("approvals", true, 5) };
    expect(keys(arrangeAppRailApps(APPS, preferences).railApps)).toEqual(["projects", "approvals", "wiki"]);
  });

  it("takes a hidden app out of the rail and lists it after the rail apps", () => {
    const preferences = { ...pref("projects", false, 0), ...pref("approvals", true, 1), ...pref("wiki", true, 2) };
    const arrangement = arrangeAppRailApps(APPS, preferences);
    expect(keys(arrangement.railApps)).toEqual(["approvals", "wiki"]);
    expect(keys(arrangement.orderedApps)).toEqual(["approvals", "wiki", "projects"]);
    // the dialog keeps the user's order and shows the hidden state
    expect(arrangement.items.map((item) => [item.app.key, item.isHidden])).toEqual([
      ["projects", true],
      ["approvals", false],
      ["wiki", false],
    ]);
  });

  it("hides nothing when every app is hidden", () => {
    const preferences = { ...pref("projects", false), ...pref("approvals", false), ...pref("wiki", false) };
    const arrangement = arrangeAppRailApps(APPS, preferences);
    expect(keys(arrangement.railApps)).toEqual(["projects", "approvals", "wiki"]);
    expect(arrangement.items.some((item) => item.isHidden)).toBe(false);
  });

  it("cannot hide a single enabled app, whatever is stored", () => {
    const arrangement = arrangeAppRailApps([projects], pref("projects", false, 3));
    expect(keys(arrangement.railApps)).toEqual(["projects"]);
  });

  it("drops the preferences of apps that are not enabled", () => {
    const preferences = { ...pref("approvals", true, 0), ...pref("wiki", true, 1), ...pref("projects", true, 2) };
    expect(keys(arrangeAppRailApps([projects, wiki], preferences).railApps)).toEqual(["wiki", "projects"]);
  });

  it("ignores a position that is not a number", () => {
    const preferences = { "app_rail:wiki": { is_pinned: true, sort_order: Number.NaN } };
    expect(keys(arrangeAppRailApps(APPS, preferences).railApps)).toEqual(["projects", "approvals", "wiki"]);
  });
});

describe("getAppRailState with preferences", () => {
  const preferences = {
    "app_rail:wiki": { is_pinned: true, sort_order: 0 },
    "app_rail:projects": { is_pinned: true, sort_order: 1 },
    "app_rail:approvals": { is_pinned: false, sort_order: 2 },
  };

  it("keeps enabled apps in registry order and arranges the rail", () => {
    const state = getAppRailState(APPS, context(), "/acme/wiki/", preferences);
    expect(state.enabledApps.map((a) => a.key)).toEqual(["projects", "approvals", "wiki"]);
    expect(state.railApps.map((a) => a.key)).toEqual(["wiki", "projects"]);
    expect(state.orderedApps.map((a) => a.key)).toEqual(["wiki", "projects", "approvals"]);
    expect(getAppRailDockItems(state, "acme").map((item) => [item.key, item.isActive])).toEqual([
      ["wiki", true],
      ["projects", false],
    ]);
  });

  it("still counts a hidden app as enabled: its routes open and it is the active app", () => {
    const state = getAppRailState(APPS, context(), "/acme/approvals/", preferences);
    expect(state.activeAppKey).toBe("approvals");
    expect(state.hasMultipleApps).toBe(true);
    expect(getAppRailRouteAccess(state.enabledApps, "approvals", "acme")).toEqual({ isAllowed: true });
    expect(getAppRailDockItems(state, "acme").some((item) => item.isActive)).toBe(false);
  });

  it("changes nothing for a single app", () => {
    const state = getAppRailState([projects], context(), "/acme/", { "app_rail:projects": { is_pinned: false } });
    expect(state.railApps.map((a) => a.key)).toEqual(["projects"]);
    expect(state.hasMultipleApps).toBe(false);
  });
});

describe("buildAppRailPreferenceUpdate and canHideAppRailApp", () => {
  const items = [
    { app: wiki, isHidden: false },
    { app: projects, isHidden: true },
    { app: approvals, isHidden: false },
  ];

  it("writes one row per app with its position", () => {
    expect(buildAppRailPreferenceUpdate(items)).toEqual([
      { key: "app_rail:wiki", is_pinned: true, sort_order: 0 },
      { key: "app_rail:projects", is_pinned: false, sort_order: 1 },
      { key: "app_rail:approvals", is_pinned: true, sort_order: 2 },
    ]);
  });

  it("round-trips through arrangeAppRailApps", () => {
    const stored = Object.fromEntries(buildAppRailPreferenceUpdate(items).map(({ key, ...rest }) => [key, rest]));
    expect(arrangeAppRailApps(APPS, stored).items.map((item) => [item.app.key, item.isHidden])).toEqual(
      items.map((item) => [item.app.key, item.isHidden])
    );
  });

  it("lets an app be hidden while another stays in the rail", () => {
    expect(canHideAppRailApp(items, "wiki")).toBe(true);
    expect(canHideAppRailApp(items, "approvals")).toBe(true);
  });

  it("does not let the last app of the rail be hidden", () => {
    const oneLeft = [
      { app: wiki, isHidden: false },
      { app: projects, isHidden: true },
    ];
    expect(canHideAppRailApp(oneLeft, "wiki")).toBe(false);
  });
});

describe("isWorkspaceRootPath", () => {
  it("is true for the workspace root only", () => {
    expect(isWorkspaceRootPath("/acme", "acme")).toBe(true);
    expect(isWorkspaceRootPath("/acme/", "acme")).toBe(true);
    expect(isWorkspaceRootPath("/acme/?tab=1#top", "acme")).toBe(true);
    expect(isWorkspaceRootPath("/acme/projects/", "acme")).toBe(false);
    expect(isWorkspaceRootPath("/acme/settings/", "acme")).toBe(false);
  });

  it("is false outside the workspace or without one", () => {
    expect(isWorkspaceRootPath("/other/", "acme")).toBe(false);
    expect(isWorkspaceRootPath("/i/PRJ-1/", "acme")).toBe(false);
    expect(isWorkspaceRootPath("/acme/", undefined)).toBe(false);
  });
});

describe("getAppRailLandingApp", () => {
  it("prefers the default app, then the last used app", () => {
    expect(getAppRailLandingApp(APPS, "wiki", "approvals")?.key).toBe("wiki");
    expect(getAppRailLandingApp(APPS, null, "approvals")?.key).toBe("approvals");
    expect(getAppRailLandingApp(APPS, undefined, undefined)).toBeUndefined();
  });

  it("skips a default app that is not enabled for the user and falls to the last used app", () => {
    expect(getAppRailLandingApp([projects, wiki], "approvals", "wiki")?.key).toBe("wiki");
    expect(getAppRailLandingApp([projects, wiki], "approvals", undefined)).toBeUndefined();
  });

  it("skips a last used app that is no longer enabled", () => {
    expect(getAppRailLandingApp([projects, wiki], undefined, "approvals")).toBeUndefined();
  });

  it("ignores keys that are not apps", () => {
    expect(getAppRailLandingApp(APPS, "nonsense", "__proto__")).toBeUndefined();
    expect(getAppRailLandingApp(APPS, "", "")).toBeUndefined();
  });

  it("lands a user without the root's app in their first enabled app", () => {
    // for example a role restricted to one app later: the root belongs to Projects, which is off
    expect(getAppRailLandingApp([approvals, wiki], undefined, undefined)?.key).toBe("approvals");
    expect(getAppRailLandingApp([wiki], "projects", "projects")?.key).toBe("wiki");
    expect(getAppRailLandingApp([], undefined, undefined)).toBeUndefined();
  });
});

describe("getAppRailLandingRedirect", () => {
  const landing = (overrides: Partial<Parameters<typeof getAppRailLandingRedirect<TKey>>[0]> = {}) =>
    getAppRailLandingRedirect<TKey>({
      enabledApps: APPS,
      pathname: "/acme/",
      workspaceSlug: "acme",
      defaultAppKey: undefined,
      lastUsedAppKey: undefined,
      ...overrides,
    });

  it("leaves the root as it is without a default or a last used app", () => {
    expect(landing()).toBeUndefined();
  });

  it("goes to the default app", () => {
    expect(landing({ defaultAppKey: "approvals" })).toBe("/acme/approvals/");
    expect(landing({ pathname: "/acme", defaultAppKey: "approvals" })).toBe("/acme/approvals/");
  });

  it("goes to the last used app when there is no default", () => {
    expect(landing({ lastUsedAppKey: "wiki" })).toBe("/acme/wiki/");
  });

  it("prefers the default app over the last used app", () => {
    expect(landing({ defaultAppKey: "approvals", lastUsedAppKey: "wiki" })).toBe("/acme/approvals/");
  });

  it("never redirects a deep link", () => {
    for (const pathname of ["/acme/projects/p1/issues/", "/acme/wiki/", "/acme/settings/", "/acme/notifications/"]) {
      expect(landing({ pathname, defaultAppKey: "approvals", lastUsedAppKey: "wiki" })).toBeUndefined();
    }
  });

  it("does not redirect to the app that already owns the root", () => {
    expect(landing({ defaultAppKey: "projects", lastUsedAppKey: "wiki" })).toBeUndefined();
    expect(landing({ lastUsedAppKey: "projects" })).toBeUndefined();
  });

  it("falls back when the default app was switched off for the user", () => {
    expect(landing({ enabledApps: [projects, wiki], defaultAppKey: "approvals", lastUsedAppKey: "wiki" })).toBe(
      "/acme/wiki/"
    );
    expect(landing({ enabledApps: [projects, wiki], defaultAppKey: "approvals" })).toBeUndefined();
  });

  it("does nothing with a single app, whatever is stored", () => {
    expect(landing({ enabledApps: [projects], defaultAppKey: "approvals", lastUsedAppKey: "wiki" })).toBeUndefined();
    expect(landing({ enabledApps: [projects], defaultAppKey: "projects" })).toBeUndefined();
  });

  it("does nothing without a workspace", () => {
    expect(landing({ workspaceSlug: undefined, defaultAppKey: "approvals" })).toBeUndefined();
  });

  it("sends a user who cannot use the root's app to their first app", () => {
    expect(landing({ enabledApps: [wiki] })).toBe("/acme/wiki/");
  });
});

describe("resolveAppRailLanding", () => {
  const input = {
    enabledApps: APPS,
    pathname: "/acme/",
    workspaceSlug: "acme",
    defaultAppKey: undefined,
    lastUsedAppKey: undefined,
    isDefaultAppKnown: true,
  };

  it("waits at the root of a multi-app workspace until the default app is known", () => {
    expect(resolveAppRailLanding({ ...input, isDefaultAppKnown: false })).toEqual({ isPending: true });
    // the last used app does not shortcut the wait: the default app would win over it
    expect(resolveAppRailLanding({ ...input, isDefaultAppKnown: false, lastUsedAppKey: "wiki" })).toEqual({
      isPending: true,
    });
  });

  it("decides once it is known", () => {
    expect(resolveAppRailLanding(input)).toEqual({ isPending: false, redirectTo: undefined });
    expect(resolveAppRailLanding({ ...input, defaultAppKey: "approvals" })).toEqual({
      isPending: false,
      redirectTo: "/acme/approvals/",
    });
  });

  it("never waits with a single app: the shell behaves as before", () => {
    expect(resolveAppRailLanding({ ...input, enabledApps: [projects], isDefaultAppKnown: false })).toEqual({
      isPending: false,
      redirectTo: undefined,
    });
  });

  it("never waits on a deep link", () => {
    expect(resolveAppRailLanding({ ...input, pathname: "/acme/projects/p1/", isDefaultAppKnown: false })).toEqual({
      isPending: false,
      redirectTo: undefined,
    });
  });
});

describe("getAppRailDefaultAppKey", () => {
  it("shows the stored app when it is enabled", () => {
    expect(getAppRailDefaultAppKey(APPS, "wiki")).toBe("wiki");
  });

  it("reads as no default when nothing is stored or the app is not enabled", () => {
    expect(getAppRailDefaultAppKey(APPS, null)).toBeUndefined();
    expect(getAppRailDefaultAppKey(APPS, undefined)).toBeUndefined();
    expect(getAppRailDefaultAppKey([projects, wiki], "approvals")).toBeUndefined();
  });
});
