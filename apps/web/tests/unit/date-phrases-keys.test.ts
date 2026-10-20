/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// `date_phrases.*` are the short sentences placed around a formatted date or a relative time ("Added
// {timeAgo}", "Expires {date} at {time}"). Keep the code, the English file and every locale in step.

const webRoot = resolve(import.meta.dirname, "../..");
const localesDir = resolve(webRoot, "../../packages/i18n/src/locales");
const phrases = (locale: string) =>
  (
    JSON.parse(readFileSync(join(localesDir, locale, "common.json"), "utf8")) as {
      date_phrases: Record<string, string>;
    }
  ).date_phrases;
const english = phrases("en");

const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (name === "node_modules" || name === "tests") return [];
    return statSync(path).isDirectory() ? walk(path) : /\.tsx?$/.test(name) ? [path] : [];
  });
const used = new Set(
  ["components", "app", "helpers", "hooks"]
    .flatMap((dir) => walk(join(webRoot, dir)))
    .flatMap((file) =>
      [...readFileSync(file, "utf8").matchAll(/"date_phrases\.([a-z_]+)"/g)].map((m) => m[1] as string)
    )
);
const variables = (text: string) => [...text.matchAll(/\{\s*(\w+)\s*\}/g)].map((m) => m[1]).sort();

describe("date_phrases translation keys", () => {
  it("defines every key the components use, and uses every key it defines", () => {
    expect([...used].filter((key) => !(key in english))).toEqual([]);
    expect(Object.keys(english).filter((key) => !used.has(key))).toEqual([]);
  });

  it.each(readdirSync(localesDir).filter((name) => name !== "en"))(
    "keeps the variables of every English phrase in %s",
    (locale) => {
      const translated = phrases(locale);
      const problems = Object.entries(english).filter(
        ([key, text]) => !translated[key] || variables(translated[key]).join() !== variables(text).join()
      );
      expect(problems.map(([key]) => key)).toEqual([]);
    }
  );
});
