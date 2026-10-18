/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// The activity feed sentences are spelled out as literal keys in the components so they stay greppable.
// This keeps the code and the English locale file in step: a key used but not defined renders as the raw
// key, and a defined key nobody uses is dead translation work.

const webRoot = resolve(import.meta.dirname, "../..");
const locale = JSON.parse(
  readFileSync(resolve(webRoot, "../../packages/i18n/src/locales/en/work-item.json"), "utf8")
) as { activity_feed: Record<string, unknown> };

const flatten = (node: unknown, prefix: string): string[] =>
  typeof node === "string"
    ? [prefix]
    : Object.entries(node as Record<string, unknown>).flatMap(([key, value]) => flatten(value, `${prefix}.${key}`));

const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (name === "node_modules" || name === "tests") return [];
    return statSync(path).isDirectory() ? walk(path) : /\.tsx?$/.test(name) ? [path] : [];
  });

const usedKeys = new Set(
  ["components", "app", "helpers", "hooks"]
    .flatMap((dir) => walk(join(webRoot, dir)))
    .flatMap((file) =>
      [...readFileSync(file, "utf8").matchAll(/"(activity_feed\.[a-z0-9_.]+)"/g)].map((m) => m[1] as string)
    )
);
const definedKeys = new Set(flatten(locale.activity_feed, "activity_feed"));

const localesDir = resolve(webRoot, "../../packages/i18n/src/locales");
const localeNames = readdirSync(localesDir).filter(
  (name) => name !== "en" && existsSync(join(localesDir, name, "work-item.json"))
);
const markup = (text: string) => [...text.matchAll(/<\/?\w+\s*\/?>/g)].map((m) => m[0].replace(/\s+/g, "")).sort();
const variables = (text: string) => [...text.matchAll(/\{\s*(\w+)\s*[,}]/g)].map((m) => m[1]).sort();
const valueAt = (tree: unknown, key: string) =>
  key
    .split(".")
    .slice(1)
    .reduce<unknown>((node, part) => (node as Record<string, unknown> | undefined)?.[part], tree);

describe("activity feed translation keys", () => {
  it("defines every key the components use", () => {
    expect([...usedKeys].filter((key) => !definedKeys.has(key))).toEqual([]);
  });

  it("uses every key the English locale defines", () => {
    expect([...definedKeys].filter((key) => !usedKeys.has(key))).toEqual([]);
  });

  it("covers the issue, profile and project feeds", () => {
    for (const area of ["issue", "profile", "project"]) {
      expect([...definedKeys].some((key) => key.startsWith(`activity_feed.${area}.`))).toBe(true);
    }
  });

  it.each(localeNames)("keeps the markup and variables of every English sentence in %s", (name) => {
    const translated = JSON.parse(readFileSync(join(localesDir, name, "work-item.json"), "utf8")) as {
      activity_feed: unknown;
    };
    const problems: string[] = [];
    for (const key of definedKeys) {
      const english = valueAt(locale.activity_feed, key) as string;
      const text = valueAt(translated.activity_feed, key) as string | undefined;
      if (typeof text !== "string" || text.trim() === "") problems.push(`${key}: missing`);
      else if (markup(text).join() !== markup(english).join() || variables(text).join() !== variables(english).join())
        problems.push(`${key}: markup or variables differ from English`);
    }
    expect(problems).toEqual([]);
  });
});
