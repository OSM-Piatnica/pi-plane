/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { PROJECT_COPY_MAX_WORK_ITEMS, PROJECT_COPY_WORK_ITEM_PROPERTY_GROUPS } from "@plane/constants";

// The duplicate form lists these properties, so one the web app does not know cannot be switched off and one
// it invents would be refused by the API.
const source = readFileSync(
  resolve(import.meta.dirname, "../../../../apps/api/plane/utils/project_copy_work_items.py"),
  "utf8"
);
const quoted = (text: string) => [...text.matchAll(/"([a-z_]+)"/g)].map((match) => match[1]);

describe("project copy constants of the API", () => {
  it("group the work item properties the same way here as in the API", () => {
    const block = source.split("WORK_ITEM_PROPERTY_GROUPS = {")[1].split("\n}\n")[0];
    const parsed = Object.fromEntries(
      [...block.matchAll(/"([a-z_]+)": \(([^)]*)\)/g)].map((match) => [match[1], quoted(match[2])])
    );

    expect(parsed).toEqual(PROJECT_COPY_WORK_ITEM_PROPERTY_GROUPS);
  });

  it("limit the work items the same way here as in the API", () => {
    const limit = /^MAX_WORK_ITEMS = ([\d_]+)/m.exec(
      readFileSync(resolve(import.meta.dirname, "../../../../apps/api/plane/utils/project_duplicate.py"), "utf8")
    );

    expect(Number(limit?.[1].replaceAll("_", ""))).toBe(PROJECT_COPY_MAX_WORK_ITEMS);
  });
});
