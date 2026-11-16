/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { APP_RAIL_MAX_SWITCH_SHORTCUTS } from "@plane/constants";
import type { TAppRailApp, TAppRailAppKey, TAppRailContext } from "@plane/types";
import {
  getActiveAppRailAppKey,
  getAppRailSwitchKeySequence,
  getEnabledAppRailApps,
  hasMultipleAppRailApps,
  validateAppRailApps,
} from "@plane/utils";
import { APP_RAIL_APPS, getAppRailApp } from "@/components/app-rail/registry";
import { APP_RAIL_SWITCH_COMMAND_ID_PREFIX, buildAppRailSwitchCommands } from "@/components/app-rail/switch-commands";
import type { TPowerKContext } from "@/components/power-k/core/types";

const CONTEXT: TAppRailContext = {
  workspaceSlug: "acme",
  workspace: undefined,
  user: undefined,
  workspaceRole: undefined,
};

// a second app that exists only in this test: production registers Projects alone
const fakeApp = (key: string): TAppRailApp =>
  ({
    key,
    i18n_label: key,
    i18n_switch_label: `app_rail.switch_to.${key}`,
    routeSegments: [key],
    getHref: (workspaceSlug: string) => `/${workspaceSlug}/${key}/`,
    isEnabled: () => true,
  }) as unknown as TAppRailApp;

const Icon = () => null;

const powerKContext = (workspaceSlug: string | undefined) => {
  const push = vi.fn();
  const ctx = { params: { workspaceSlug }, router: { push } } as unknown as TPowerKContext;
  return { ctx, push };
};

// the English locale: every namespace file, merged the way the app sees it
const EN_LOCALE_DIRECTORY = path.resolve(import.meta.dirname, "../../../../packages/i18n/src/locales/en");
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

describe("APP_RAIL_APPS", () => {
  it("is a consistent registry", () => {
    expect(validateAppRailApps(APP_RAIL_APPS)).toEqual([]);
  });

  it("registers Projects first, as the default app", () => {
    expect(APP_RAIL_APPS[0].key).toBe("projects");
    expect(APP_RAIL_APPS[0].isDefault).toBe(true);
    expect(getAppRailApp("projects")).toBe(APP_RAIL_APPS[0]);
  });

  it("offers Projects alone, so the rail and the switch commands stay off", () => {
    const enabled = getEnabledAppRailApps(APP_RAIL_APPS, CONTEXT);
    expect(enabled.map((app) => app.key)).toEqual<TAppRailAppKey[]>(["projects"]);
    expect(hasMultipleAppRailApps(enabled)).toBe(false);
    expect(buildAppRailSwitchCommands(enabled)).toEqual([]);
  });

  it("keeps the label, link and active state of the former hard-coded Projects item", () => {
    const projects = APP_RAIL_APPS[0];
    expect(projects.i18n_label).toBe("projects");
    expect(projects.getHref("acme")).toBe("/acme/");
    expect(getActiveAppRailAppKey(APP_RAIL_APPS, "/acme/", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(APP_RAIL_APPS, "/acme/projects/p1/issues/", "acme")).toBe("projects");
    expect(getActiveAppRailAppKey(APP_RAIL_APPS, "/acme/notifications/", "acme")).toBeUndefined();
    expect(getActiveAppRailAppKey(APP_RAIL_APPS, "/acme/settings/", "acme")).toBeUndefined();
  });

  it("uses labels that exist in the English locale", () => {
    for (const app of APP_RAIL_APPS) {
      expect(hasEnglishString(app.i18n_label)).toBe(true);
      expect(hasEnglishString(app.i18n_switch_label)).toBe(true);
    }
  });
});

describe("buildAppRailSwitchCommands", () => {
  const twoApps = [APP_RAIL_APPS[0], fakeApp("approvals")];

  it("returns nothing for no app or a single app", () => {
    expect(buildAppRailSwitchCommands([])).toEqual([]);
    expect(buildAppRailSwitchCommands([APP_RAIL_APPS[0]])).toEqual([]);
  });

  it("creates one navigation command per app, in rail order, with g1, g2, ... sequences", () => {
    const commands = buildAppRailSwitchCommands(twoApps);
    expect(commands.map((command) => command.id)).toEqual([
      `${APP_RAIL_SWITCH_COMMAND_ID_PREFIX}projects`,
      `${APP_RAIL_SWITCH_COMMAND_ID_PREFIX}approvals`,
    ]);
    expect(commands.map((command) => command.keySequence)).toEqual(["g1", "g2"]);
    expect(commands.map((command) => command.i18n_title)).toEqual([
      "app_rail.switch_to.projects",
      "app_rail.switch_to.approvals",
    ]);
    expect(commands.every((command) => command.group === "navigation" && command.closeOnSelect)).toBe(true);
  });

  it("navigates to the app's href", () => {
    const { ctx, push } = powerKContext("acme");
    const [, approvals] = buildAppRailSwitchCommands(twoApps);
    if (approvals.type !== "action") throw new Error("expected an action command");
    void approvals.action(ctx);
    expect(push).toHaveBeenCalledWith("/acme/approvals/");
  });

  it("is hidden, disabled and inert outside a workspace", () => {
    const { ctx, push } = powerKContext(undefined);
    const [projects] = buildAppRailSwitchCommands(twoApps);
    expect(projects.isVisible(ctx)).toBe(false);
    expect(projects.isEnabled(ctx)).toBe(false);
    if (projects.type !== "action") throw new Error("expected an action command");
    void projects.action(ctx);
    expect(push).not.toHaveBeenCalled();

    const inWorkspace = powerKContext("acme").ctx;
    expect(projects.isVisible(inWorkspace)).toBe(true);
    expect(projects.isEnabled(inWorkspace)).toBe(true);
  });

  it("attaches the icons it is given", () => {
    const [projects, approvals] = buildAppRailSwitchCommands(twoApps, { projects: Icon });
    expect(projects.icon).toBe(Icon);
    expect(approvals.icon).toBeUndefined();
  });

  it("leaves apps beyond the ninth without a shortcut", () => {
    const manyApps = Array.from({ length: APP_RAIL_MAX_SWITCH_SHORTCUTS + 2 }, (_, index) => fakeApp(`app${index}`));
    const commands = buildAppRailSwitchCommands(manyApps);
    expect(commands).toHaveLength(manyApps.length);
    expect(commands[APP_RAIL_MAX_SWITCH_SHORTCUTS - 1].keySequence).toBe("g9");
    expect(commands[APP_RAIL_MAX_SWITCH_SHORTCUTS].keySequence).toBeUndefined();
  });
});

describe("app switching shortcuts", () => {
  // every key sequence and single-key shortcut written as a literal in the command palette sources
  const collectLiterals = (directory: string, found: { sequences: Set<string>; singles: Set<string> }) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const entryPath = path.join(directory, entry.name);
      if (entry.isDirectory()) collectLiterals(entryPath, found);
      else if (/\.tsx?$/.test(entry.name)) {
        const source = readFileSync(entryPath, "utf8");
        for (const match of source.matchAll(/\bkeySequence:\s*"([^"]+)"/g)) found.sequences.add(match[1]);
        for (const match of source.matchAll(/\bshortcut:\s*"([^"]+)"/g)) found.singles.add(match[1]);
      }
    }
    return found;
  };
  const existing = collectLiterals(path.resolve(import.meta.dirname, "../../components/power-k"), {
    sequences: new Set(),
    singles: new Set(),
  });
  const generated = Array.from({ length: APP_RAIL_MAX_SWITCH_SHORTCUTS }, (_, index) =>
    getAppRailSwitchKeySequence(index)
  );

  it("finds the existing bindings it checks against", () => {
    expect(existing.sequences.has("gh")).toBe(true);
    expect(existing.singles.size).toBeGreaterThan(0);
  });

  it("do not collide with a key sequence of the command palette", () => {
    for (const sequence of generated) {
      expect(sequence).toMatch(/^g[1-9]$/);
      expect(existing.sequences.has(sequence as string)).toBe(false);
    }
  });

  it("reuse an existing sequence prefix, so no single-key shortcut gets shadowed", () => {
    // a sequence prefix swallows the single-key shortcut on the same key (see ShortcutHandler)
    const existingPrefixes = new Set([...existing.sequences].map((sequence) => sequence[0]));
    expect(existingPrefixes.has("g")).toBe(true);
    expect(existing.singles.has("g")).toBe(false);
    // and no existing sequence continues past a generated one or stops short of it
    for (const sequence of existing.sequences) {
      expect(generated.some((own) => own?.startsWith(sequence) || sequence.startsWith(own as string))).toBe(false);
    }
  });
});
