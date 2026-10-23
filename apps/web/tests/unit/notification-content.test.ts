/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { renderAdditionalAction } from "../../components/workspace-notifications/notification-card/content";

const localesDir = join(__dirname, "../../../../packages/i18n/src/locales");
const readContent = (locale: string): Record<string, string> =>
  JSON.parse(readFileSync(join(localesDir, locale, "notification.json"), "utf8")).notification.content;

const identityT = (key: string) => key;

describe("renderAdditionalAction", () => {
  it("picks the phrase of the field and verb", () => {
    expect(renderAdditionalAction("state", "updated", identityT)).toBe("notification.content.state_updated");
    expect(renderAdditionalAction("cycles", "created", identityT)).toBe("notification.content.cycle_added");
    expect(renderAdditionalAction("cycles", "deleted", identityT)).toBe("notification.content.cycle_removed");
    expect(renderAdditionalAction("link", "updated", identityT)).toBe("notification.content.link_updated");
  });

  it("falls back to the phrase of another verb of the same field", () => {
    expect(renderAdditionalAction("priority", "created", identityT)).toBe("notification.content.priority_updated");
  });

  it("uses the generic phrase for a field it does not know", () => {
    expect(renderAdditionalAction("something_new", "updated", identityT)).toBe("notification.content.generic_updated");
  });
});

describe("notification content translations", () => {
  const sources = [
    "../../components/workspace-notifications/sidebar/notification-card/content.tsx",
    "../../components/workspace-notifications/notification-card/content.ts",
  ].map((path) => readFileSync(join(__dirname, path), "utf8"));
  const usedKeys = new Set(
    sources.flatMap((source) => [...source.matchAll(/notification\.content\.([a-z_]+)/g)].map((match) => match[1]))
  );

  it("has every key the components use in English", () => {
    const english = readContent("en");
    for (const key of usedKeys) expect(english, key).toHaveProperty(key);
  });

  it("has the same keys in every locale, with the value placeholder written the same way", () => {
    const english = readContent("en");
    for (const locale of readdirSync(localesDir)) {
      const content = readContent(locale);
      expect(Object.keys(content).toSorted(), locale).toEqual(Object.keys(english).toSorted());
      for (const [key, value] of Object.entries(content)) {
        expect(value.replace(/<value\/>/g, ""), `${locale}.${key}`).not.toMatch(/[<>]/);
        expect(value.trim(), `${locale}.${key}`).not.toBe("");
      }
    }
  });
});
