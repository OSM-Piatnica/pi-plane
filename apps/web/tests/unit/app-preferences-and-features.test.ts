/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import {
  APP_RAIL_LAST_USED_APP_STORAGE_KEY_PREFIX,
  APP_RAIL_PREFERENCE_KEY_PREFIX,
  GROUPED_WORKSPACE_SETTINGS,
  WORKSPACE_FEATURE_LIST,
  WORKSPACE_SETTINGS,
  WORKSPACE_SETTINGS_ACCESS,
  isWorkspaceSettingsItemAvailable,
} from "@plane/constants";
import { EUserWorkspaceRoles } from "@plane/types";
import type { IWorkspace, TAppRailApp, TAppRailContext, TWorkspaceFeature } from "@plane/types";
import {
  getAppRailState,
  getAvailableWorkspaceFeatures,
  getEnabledAppRailApps,
  getWorkspaceFeatureFlags,
  resolveAppRailLanding,
} from "@plane/utils";
import { getLastUsedAppStorageKey, readLastUsedApp, writeLastUsedApp } from "@/components/app-rail/last-used-app";
import { APP_RAIL_APPS } from "@/components/app-rail/registry";
import { buildAppRailSwitchCommands } from "@/components/app-rail/switch-commands";
import { WorkspaceFeatureStore } from "@/store/workspace/feature.store";

vi.mock("@/services/workspace.service", () => ({
  WorkspaceService: class {
    updateWorkspaceFeatures = vi.fn();
  },
}));

type TUpdateWorkspaceFeatures = (
  workspaceSlug: string,
  data: Record<string, boolean>
) => Promise<Record<string, boolean>>;

const memoryStorage = () => {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => void values.set(key, value),
  };
};

const REPOSITORY_ROOT = path.resolve(import.meta.dirname, "../../../..");
const readApiSource = (file: string) => readFileSync(path.join(REPOSITORY_ROOT, "apps/api/plane/utils", file), "utf8");

// the English locale: every namespace file, merged the way the app sees it
const EN_LOCALE_DIRECTORY = path.join(REPOSITORY_ROOT, "packages/i18n/src/locales/en");
const EN_NAMESPACES: unknown[] = readdirSync(EN_LOCALE_DIRECTORY)
  .filter((file) => file.endsWith(".json"))
  .map((file) => JSON.parse(readFileSync(path.join(EN_LOCALE_DIRECTORY, file), "utf8")));
const hasEnglishString = (key: string): boolean =>
  EN_NAMESPACES.some(
    (namespace) =>
      typeof key
        .split(".")
        .reduce<unknown>(
          (node, part) => (node && typeof node === "object" ? (node as Record<string, unknown>)[part] : undefined),
          namespace
        ) === "string"
  );

// apps and features that exist only in these tests: production has Projects and Initiatives (behind its switch)
const projects = APP_RAIL_APPS[0];
const fakeApp = (key: string, overrides: Partial<TAppRailApp> = {}): TAppRailApp =>
  ({
    key,
    i18n_label: key,
    i18n_switch_label: `app_rail.switch_to.${key}`,
    routeSegments: [key],
    getHref: (workspaceSlug: string) => `/${workspaceSlug}/${key}/`,
    isEnabled: () => true,
    ...overrides,
  }) as unknown as TAppRailApp;

const context = (overrides: Partial<TAppRailContext> = {}): TAppRailContext => ({
  workspaceSlug: "acme",
  workspace: undefined,
  user: undefined,
  workspaceRole: undefined,
  features: getWorkspaceFeatureFlags(undefined),
  ...overrides,
});

describe("the lists the API validates against", () => {
  it("knows the same rail apps as the registry", () => {
    const source = readApiSource("app_rail.py");
    const tuple = source.match(/^APP_RAIL_APP_KEYS = \(([^)]*)\)/m)?.[1];
    expect(tuple).toBeDefined();
    const apiKeys = [...(tuple as string).matchAll(/"([^"]+)"/g)].map((match) => match[1]);
    expect(apiKeys).toEqual(APP_RAIL_APPS.map((app) => app.key));
  });

  it("uses the same preference key prefix", () => {
    const prefix = readApiSource("app_rail.py").match(/^APP_RAIL_PREFERENCE_KEY_PREFIX = "([^"]+)"/m)?.[1];
    expect(prefix).toBe(APP_RAIL_PREFERENCE_KEY_PREFIX);
  });

  it("knows the same feature switches, with the same availability", () => {
    const source = readApiSource("workspace_features.py");
    const body = source.match(/^WORKSPACE_FEATURES = \{([^}]*)\}/m)?.[1];
    expect(body).toBeDefined();
    const apiFeatures = [...(body as string).matchAll(/"([^"]+)": (True|False)/g)].map((match) => ({
      key: match[1],
      isAvailable: match[2] === "True",
    }));
    expect(apiFeatures.length).toBeGreaterThan(0);
    expect(apiFeatures).toEqual(WORKSPACE_FEATURE_LIST.map(({ key, isAvailable }) => ({ key, isAvailable })));
  });
});

describe("what ships: Projects, and Initiatives behind its switch", () => {
  it("offers the Initiatives switch and nothing else", () => {
    expect(getAvailableWorkspaceFeatures().map((feature) => feature.key)).toEqual(["initiatives"]);
  });

  it("has a Features entry in the settings sidebar", () => {
    expect(isWorkspaceSettingsItemAvailable(WORKSPACE_SETTINGS.features)).toBe(true);
    const sidebarKeys = Object.values(GROUPED_WORKSPACE_SETTINGS)
      .flat()
      .map((item) => item.key);
    expect(sidebarKeys).toContain("features");
    expect(sidebarKeys).toEqual(expect.arrayContaining(["general", "members", "groups", "export", "webhooks"]));
  });

  it("enables Initiatives for members once the switch is on, never for guests", () => {
    const on = { ...getWorkspaceFeatureFlags(undefined), initiatives: true };
    const keys = (overrides: Partial<TAppRailContext>) =>
      getEnabledAppRailApps(APP_RAIL_APPS, context(overrides)).map((app) => app.key);
    expect(keys({ features: on, workspaceRole: EUserWorkspaceRoles.MEMBER })).toEqual(["projects", "initiatives"]);
    expect(keys({ features: on, workspaceRole: EUserWorkspaceRoles.ADMIN })).toEqual(["projects", "initiatives"]);
    expect(keys({ features: on, workspaceRole: EUserWorkspaceRoles.GUEST })).toEqual(["projects"]);
    expect(keys({ features: on })).toEqual(["projects"]);
    expect(keys({ workspaceRole: EUserWorkspaceRoles.ADMIN })).toEqual(["projects"]);
  });

  it("keeps Projects enabled whatever the feature switches say", () => {
    const allOn = { lite: true, approvals: true, initiatives: true, wiki: true, raci: true };
    for (const features of [getWorkspaceFeatureFlags(undefined), allOn])
      expect(getEnabledAppRailApps(APP_RAIL_APPS, context({ features })).map((app) => app.key)).toEqual(["projects"]);
  });

  it("ignores stored app preferences and never waits or redirects at the workspace root", () => {
    const preferences = { "app_rail:projects": { is_pinned: false, sort_order: 4 } };
    const state = getAppRailState(APP_RAIL_APPS, context(), "/acme/", preferences);
    expect(state.railApps.map((app) => app.key)).toEqual(["projects"]);
    expect(state.hasMultipleApps).toBe(false);
    expect(buildAppRailSwitchCommands(state.orderedApps)).toEqual([]);
    expect(
      resolveAppRailLanding({
        enabledApps: state.enabledApps,
        pathname: "/acme/",
        workspaceSlug: "acme",
        defaultAppKey: "approvals",
        lastUsedAppKey: "approvals",
        isDefaultAppKnown: false,
      })
    ).toEqual({ isPending: false, redirectTo: undefined });
  });
});

describe("the Features settings page", () => {
  const withOneAvailable: TWorkspaceFeature[] = [
    { key: "approvals", isAvailable: true, i18n_title: "x.title", i18n_description: "x.description" },
    { key: "wiki", isAvailable: false },
  ];

  it("appears once a feature is available", () => {
    expect(isWorkspaceSettingsItemAvailable(WORKSPACE_SETTINGS.features, withOneAvailable)).toBe(true);
    expect(isWorkspaceSettingsItemAvailable(WORKSPACE_SETTINGS.features, [{ isAvailable: false }])).toBe(false);
    expect(isWorkspaceSettingsItemAvailable(WORKSPACE_SETTINGS.features, [])).toBe(false);
  });

  it("is for workspace admins only", () => {
    expect(WORKSPACE_SETTINGS.features.access).toEqual([EUserWorkspaceRoles.ADMIN]);
    expect(WORKSPACE_SETTINGS_ACCESS["/settings/features"]).toEqual([EUserWorkspaceRoles.ADMIN]);
  });

  it("has its strings in the English locale", () => {
    expect(hasEnglishString(WORKSPACE_SETTINGS.features.i18n_label)).toBe(true);
    expect(hasEnglishString("workspace_features.description")).toBe(true);
    expect(hasEnglishString("something_went_wrong_please_try_again")).toBe(true);
  });

  it("has a title and a description for every available feature", () => {
    for (const feature of getAvailableWorkspaceFeatures()) {
      expect(hasEnglishString(feature.i18n_title)).toBe(true);
      expect(hasEnglishString(feature.i18n_description)).toBe(true);
    }
  });
});

describe("the app preferences of the customise dialog", () => {
  it("has its strings in the English locale", () => {
    for (const key of ["heading", "default_app", "default_app_description", "last_used_app"])
      expect(hasEnglishString(`app_rail.preferences.${key}`)).toBe(true);
    expect(hasEnglishString("customize_navigation")).toBe(true);
  });
});

describe("a feature-gated app", () => {
  const approvals = fakeApp("approvals", { isEnabled: ({ features }) => features.approvals });
  const apps = [projects, approvals];
  // the flags as the hook builds them, from a workspace payload and a list where the feature is available
  const features: TWorkspaceFeature[] = [
    { key: "approvals", isAvailable: true, i18n_title: "x.title", i18n_description: "x.description" },
  ];
  const flagsOf = (workspace: Pick<IWorkspace, "enabled_features"> | undefined) => ({
    ...getWorkspaceFeatureFlags(undefined),
    ...getWorkspaceFeatureFlags(workspace?.enabled_features, features),
  });

  it("is off while the workspace loads and when the switch is off", () => {
    for (const workspace of [undefined, {}, { enabled_features: [] }, { enabled_features: ["wiki"] }]) {
      const state = getAppRailState(apps, context({ features: flagsOf(workspace) }), "/acme/");
      expect(state.enabledApps.map((app) => app.key)).toEqual(["projects"]);
      expect(state.hasMultipleApps).toBe(false);
    }
  });

  it("joins the rail, the switch commands and the shortcuts when the switch is on", () => {
    const state = getAppRailState(apps, context({ features: flagsOf({ enabled_features: ["approvals"] }) }), "/acme/");
    expect(state.railApps.map((app) => app.key)).toEqual(["projects", "approvals"]);
    expect(state.hasMultipleApps).toBe(true);
    expect(buildAppRailSwitchCommands(state.orderedApps).map((command) => command.keySequence)).toEqual(["g1", "g2"]);
  });
});

describe("switch commands with a user's arrangement", () => {
  const apps = [projects, fakeApp("approvals"), fakeApp("wiki")];
  const preferences = {
    "app_rail:wiki": { is_pinned: true, sort_order: 0 },
    "app_rail:projects": { is_pinned: false, sort_order: 1 },
    "app_rail:approvals": { is_pinned: true, sort_order: 2 },
  };

  it("number the shortcuts by position in the rail and keep hidden apps reachable after them", () => {
    const state = getAppRailState(apps, context(), "/acme/", preferences);
    const commands = buildAppRailSwitchCommands(state.orderedApps);
    expect(commands.map((command) => [command.i18n_title, command.keySequence])).toEqual([
      ["app_rail.switch_to.wiki", "g1"],
      ["app_rail.switch_to.approvals", "g2"],
      ["app_rail.switch_to.projects", "g3"],
    ]);
  });
});

describe("last used app", () => {
  const brokenStorage = {
    getItem: () => {
      throw new Error("storage is blocked");
    },
    setItem: () => {
      throw new Error("quota exceeded");
    },
  };

  it("is kept per workspace", () => {
    const storage = memoryStorage();
    writeLastUsedApp("acme", "approvals", storage);
    writeLastUsedApp("other", "wiki", storage);
    expect(readLastUsedApp("acme", storage)).toBe("approvals");
    expect(readLastUsedApp("other", storage)).toBe("wiki");
    expect(readLastUsedApp("third", storage)).toBeUndefined();
    expect(getLastUsedAppStorageKey("acme")).toBe(`${APP_RAIL_LAST_USED_APP_STORAGE_KEY_PREFIX}acme`);
    expect([...storage.values.keys()]).toEqual(["APP_RAIL_LAST_APP_acme", "APP_RAIL_LAST_APP_other"]);
  });

  it("is overwritten by the next app", () => {
    const storage = memoryStorage();
    writeLastUsedApp("acme", "approvals", storage);
    writeLastUsedApp("acme", "projects", storage);
    expect(readLastUsedApp("acme", storage)).toBe("projects");
  });

  it("reads as nothing and writes nothing when storage throws or is missing", () => {
    expect(readLastUsedApp("acme", brokenStorage)).toBeUndefined();
    expect(() => writeLastUsedApp("acme", "approvals", brokenStorage)).not.toThrow();
    // outside the browser (this test runs in node) there is no storage at all
    expect(readLastUsedApp("acme")).toBeUndefined();
    expect(() => writeLastUsedApp("acme", "approvals")).not.toThrow();
  });

  it("feeds the landing decision, after the default app", () => {
    const storage = memoryStorage();
    writeLastUsedApp("acme", "wiki", storage);
    const input = {
      enabledApps: [projects, fakeApp("approvals"), fakeApp("wiki")],
      pathname: "/acme/",
      workspaceSlug: "acme",
      lastUsedAppKey: readLastUsedApp("acme", storage),
      isDefaultAppKnown: true,
    };
    expect(resolveAppRailLanding({ ...input, defaultAppKey: null })).toEqual({
      isPending: false,
      redirectTo: "/acme/wiki/",
    });
    expect(resolveAppRailLanding({ ...input, defaultAppKey: "approvals" })).toEqual({
      isPending: false,
      redirectTo: "/acme/approvals/",
    });
    expect(resolveAppRailLanding({ ...input, defaultAppKey: "approvals", pathname: "/acme/projects/" })).toEqual({
      isPending: false,
      redirectTo: undefined,
    });
  });
});

describe("WorkspaceFeatureStore.updateFeature", () => {
  const features: TWorkspaceFeature[] = [
    { key: "approvals", isAvailable: true, i18n_title: "x.title", i18n_description: "x.description" },
    { key: "wiki", isAvailable: true, i18n_title: "y.title", i18n_description: "y.description" },
    { key: "raci", isAvailable: false },
  ];
  const createStore = (enabled_features: string[] | undefined, updateWorkspaceFeatures: TUpdateWorkspaceFeatures) => {
    const source = {
      workspaces: { w1: { id: "w1", slug: "acme", enabled_features } as unknown as IWorkspace },
      getWorkspaceBySlug: (slug: string) => Object.values(source.workspaces).find((w) => w.slug === slug) ?? null,
    };
    return { source, store: new WorkspaceFeatureStore(source, { updateWorkspaceFeatures }, features) };
  };

  it("switches the feature on at once and then takes the server's answer", async () => {
    const answers: ((states: Record<string, boolean>) => void)[] = [];
    const request = vi.fn<TUpdateWorkspaceFeatures>(
      () =>
        new Promise((resolve) => {
          answers.push(resolve);
        })
    );
    const { source, store } = createStore(["wiki"], request);

    const pending = store.updateFeature("acme", "approvals", true);
    expect(source.workspaces.w1.enabled_features).toEqual(["approvals", "wiki"]);
    expect(request).toHaveBeenCalledWith("acme", { approvals: true });

    answers[0]({ approvals: true, wiki: false });
    await pending;
    expect(source.workspaces.w1.enabled_features).toEqual(["approvals"]);
  });

  it("switches a feature off", async () => {
    const request = vi.fn<TUpdateWorkspaceFeatures>().mockResolvedValue({ approvals: false, wiki: true });
    const { source, store } = createStore(["approvals", "wiki"], request);

    await store.updateFeature("acme", "approvals", false);

    expect(request).toHaveBeenCalledWith("acme", { approvals: false });
    expect(source.workspaces.w1.enabled_features).toEqual(["wiki"]);
  });

  it("puts the previous state back and rethrows when the request fails", async () => {
    const failure = { approvals: "This feature is not available" };
    const { source, store } = createStore(["wiki"], vi.fn<TUpdateWorkspaceFeatures>().mockRejectedValue(failure));

    await expect(store.updateFeature("acme", "approvals", true)).rejects.toBe(failure);

    expect(source.workspaces.w1.enabled_features).toEqual(["wiki"]);
  });

  it("rejects for a workspace it does not know, without a request", async () => {
    const request = vi.fn<TUpdateWorkspaceFeatures>();
    const { store } = createStore([], request);

    await expect(store.updateFeature("elsewhere", "approvals", true)).rejects.toThrow("Workspace not found");
    expect(request).not.toHaveBeenCalled();
  });
});
