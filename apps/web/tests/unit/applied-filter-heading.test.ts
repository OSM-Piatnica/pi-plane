/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getAppliedFilterHeading } from "../../helpers/applied-filter-heading";

const t = (key: string) => `[${key}]`;

describe("getAppliedFilterHeading", () => {
  it("translates the filter properties of the cycle, module, project, view and page lists", () => {
    expect(getAppliedFilterHeading("status", t)).toBe("[module_ui.status]");
    expect(getAppliedFilterHeading("start_date", t)).toBe("[start_date]");
    expect(getAppliedFilterHeading("target_date", t)).toBe("[target_date]");
    expect(getAppliedFilterHeading("created_at", t)).toBe("[common.created_at]");
    expect(getAppliedFilterHeading("owned_by", t)).toBe("[filter_headings.owned_by]");
  });

  it("shows the views' view_type filter as Access, like the project filter", () => {
    expect(getAppliedFilterHeading("view_type", t)).toBe("[filter_headings.access]");
    expect(getAppliedFilterHeading("access", t)).toBe("[filter_headings.access]");
  });

  it("falls back to the property name, with underscores replaced, for an unknown filter", () => {
    expect(getAppliedFilterHeading("some_new_filter", t)).toBe("some new filter");
  });
});
