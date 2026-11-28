/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { RACI_ITEM_WARNINGS, RACI_NOTIFICATION_EVENTS } from "@plane/types";
import { countRaciWarnings, isDefaultRaciNotificationMatrix, toggleRaciNotificationRole } from "@plane/utils";

const LOCALES = path.resolve(import.meta.dirname, "../../../../packages/i18n/src/locales");
const raciOf = (locale: string) =>
  JSON.parse(readFileSync(path.join(LOCALES, locale, "pi-extensions.json"), "utf8")).raci as {
    notifications: { events: Record<string, string> };
    warnings: { kinds: Record<string, string>; reasons: Record<string, string> };
  };

describe("toggleRaciNotificationRole", () => {
  it("adds a role in the order of the roles", () => {
    expect(toggleRaciNotificationRole(["informed", "responsible"], "approver")).toEqual([
      "responsible",
      "approver",
      "informed",
    ]);
  });

  it("removes a ticked role", () => {
    expect(toggleRaciNotificationRole(["responsible", "consulted"], "responsible")).toEqual(["consulted"]);
  });

  it("starts from nothing", () => {
    expect(toggleRaciNotificationRole(undefined, "informed")).toEqual(["informed"]);
  });
});

describe("isDefaultRaciNotificationMatrix", () => {
  const defaults = { comment: ["responsible", "consulted"] as const, completed: ["informed"] as const };

  it("ignores the order of the roles", () => {
    expect(
      isDefaultRaciNotificationMatrix(
        { comment: ["consulted", "responsible"], completed: ["informed"] },
        { comment: [...defaults.comment], completed: [...defaults.completed] }
      )
    ).toBe(true);
  });

  it("sees a changed event", () => {
    expect(
      isDefaultRaciNotificationMatrix(
        { comment: ["responsible"], completed: ["informed"] },
        { comment: [...defaults.comment], completed: [...defaults.completed] }
      )
    ).toBe(false);
  });
});

describe("countRaciWarnings", () => {
  it("adds up every kind", () => {
    expect(countRaciWarnings({ no_responsible: 2, no_successor: 1, department_without_members: 3 })).toBe(6);
  });

  it("is zero without an answer", () => {
    expect(countRaciWarnings(undefined)).toBe(0);
  });
});

describe("translations", () => {
  const locales = readdirSync(LOCALES);

  it.each(locales)("%s names every event, warning and reason", (locale) => {
    const raci = raciOf(locale);
    for (const event of RACI_NOTIFICATION_EVENTS) expect(raci.notifications.events[event]).toBeTruthy();
    for (const kind of [...RACI_ITEM_WARNINGS, "department_without_members"])
      expect(raci.warnings.kinds[kind]).toBeTruthy();
    for (const reason of ["inactive", "no_members", "no_project_members"])
      expect(raci.warnings.reasons[reason]).toBeTruthy();
  });
});
