/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// A constant that carries a translation key (`i18n_label`, `titleTranslationKey`, ...) but names a key no
// English file defines renders the raw key in the UI, in every language (seen on the cycles order-by menu).
const CONSTANTS_SRC = resolve(import.meta.dirname, "../../constants/src");
const EN_DIR = resolve(import.meta.dirname, "../src/locales/en");

const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : path.endsWith(".ts") ? [path] : [];
  });

const flatten = (node: unknown, prefix: string, out: Set<string>) => {
  if (typeof node === "string") out.add(prefix);
  else if (node && typeof node === "object")
    for (const [k, v] of Object.entries(node)) flatten(v, prefix ? `${prefix}.${k}` : k, out);
};

const englishKeys = new Set<string>();
for (const file of readdirSync(EN_DIR).filter((f) => f.endsWith(".json")))
  flatten(JSON.parse(readFileSync(join(EN_DIR, file), "utf8")), "", englishKeys);

// Keys named in a constant that no code renders yet (the dashboard chart palettes, the one date filter with an
// i18n_name that the filters never read). Drop an entry when its key is added; the test below fails when one is
// listed but no longer missing.
const NOT_RENDERED_YET = new Set([
  "dashboards.widget.color_palettes.modern",
  "dashboards.widget.color_palettes.horizon",
  "dashboards.widget.color_palettes.earthen",
  "date_filters.1_month_ago",
]);

// property names that hold a key, with a plain string literal value (computed keys are not checked)
const KEY_PROPERTY = /\b(i18n_[a-z_]+|[a-zA-Z]*TranslationKey|i18n[A-Za-z]*Key)\s*:\s*"([a-z0-9_.-]+\.[a-z0-9_.-]+)"/g;

describe("translation keys named in packages/constants", () => {
  const referenced = walk(CONSTANTS_SRC).flatMap((file) =>
    [...readFileSync(file, "utf8").matchAll(KEY_PROPERTY)].map((m) => ({
      key: m[2],
      file: file.slice(CONSTANTS_SRC.length + 1),
    }))
  );

  it("finds the keys it is supposed to check", () => {
    expect(referenced.length).toBeGreaterThan(100);
  });

  it("are all defined in the English locale", () => {
    const missing = referenced
      .filter(({ key }) => !englishKeys.has(key) && !NOT_RENDERED_YET.has(key))
      .map(({ key, file }) => `${key} (${file})`);
    expect([...new Set(missing)]).toEqual([]);
  });

  it("lists no key in NOT_RENDERED_YET that is defined by now", () => {
    expect([...NOT_RENDERED_YET].filter((key) => englishKeys.has(key))).toEqual([]);
  });
});
