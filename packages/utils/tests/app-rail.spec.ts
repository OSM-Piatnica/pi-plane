/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAppRailApp, TAppRailContext } from "@plane/types";
import {
  getActiveAppRailAppKey,
  getAppRailSwitchKeySequence,
  getEnabledAppRailApps,
  hasMultipleAppRailApps,
  validateAppRailApps,
} from "../src/app-rail";

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
