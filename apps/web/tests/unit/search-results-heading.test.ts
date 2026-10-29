/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { splitTaggedText } from "@/helpers/tagged-text";

// The heading above the results of the "add existing work items" modal shows what the user typed. That text
// must be rendered by the `<query/>` placeholder and never spliced into the translated string, which is parsed
// for tags: a search for `</query>` or `<b>x</b>` would otherwise be cut up or lose its markup.

const localesDir = resolve(import.meta.dirname, "../../../../packages/i18n/src/locales");
const heading = (locale: string) =>
  (
    JSON.parse(readFileSync(join(localesDir, locale, "work-item.json"), "utf8")) as {
      issue_ui: { search_results_for_in_project: string };
    }
  ).issue_ui.search_results_for_in_project;

describe("issue_ui.search_results_for_in_project", () => {
  it.each(readdirSync(localesDir))("%s has one <query/> placeholder and no {query} variable", (locale) => {
    const text = heading(locale);
    expect(text.match(/<query\s*\/>/g)).toHaveLength(1);
    expect(text).not.toContain("{query}");
    expect(text).not.toMatch(/<query>/);
  });

  it("leaves the placeholder as its own part, so the typed text can be rendered separately", () => {
    const parts = splitTaggedText(heading("en"));
    expect(parts).toContainEqual({ tag: "query", text: "" });
    expect(parts.filter((part) => typeof part === "string").join("")).toBe('Search results for "" in project:');
  });
});
