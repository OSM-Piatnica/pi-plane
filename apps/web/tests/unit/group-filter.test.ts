/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { IModule, TFilterableUserGroup } from "@plane/types";
import {
  getGroupFilterOptions,
  getGroupFilterPathLabel,
  getGroupFilterValueLabel,
  isGroupFilterKeyword,
  matchesGroupFilter,
  shouldFilterModule,
} from "@plane/utils";

const group = (id: string, name: string, parent_id: string | null = null): TFilterableUserGroup => ({
  id,
  name,
  source: "local",
  parent_id,
  is_member: false,
});

const ROOT = group("g-root", "Production");
const CHILD = group("g-child", "Night shift", "g-root");
const OTHER = group("g-other", "Accounting");
const GROUPS = [CHILD, ROOT, OTHER];
const t = (key: string) => `[${key}]`;

describe("group filter options", () => {
  it("starts with the two keywords, then the groups by path label", () => {
    const options = getGroupFilterOptions(GROUPS);
    expect(options.map((o) => o.value)).toEqual(["my_groups", "none", "g-other", "g-root", "g-child"]);
    expect(options.map((o) => o.label)).toEqual([
      "My groups",
      "No group",
      "Accounting",
      "Production",
      "Production / Night shift",
    ]);
    expect(options.filter((o) => o.isKeyword).map((o) => o.value)).toEqual(["my_groups", "none"]);
  });

  it("translates the keyword labels only", () => {
    const options = getGroupFilterOptions(GROUPS, t);
    expect(options[0].label).toBe("[group_filter.my_groups]");
    expect(options[1].label).toBe("[group_filter.no_group]");
    expect(options[2].label).toBe("Accounting");
  });

  it("ends a path at a parent the person may not see and does not loop on a cycle", () => {
    const orphan = group("g-orphan", "Child", "g-hidden");
    expect(getGroupFilterPathLabel(orphan, new Map([[orphan.id, orphan]]))).toBe("Child");
    const a = group("a", "A", "b");
    const b = group("b", "B", "a");
    expect(getGroupFilterPathLabel(a, new Map([a, b].map((g) => [g.id, g])))).toBe("B / A");
  });

  it("labels applied values: keywords, known groups, null for an unknown group", () => {
    expect(getGroupFilterValueLabel("none", GROUPS, t)).toBe("[group_filter.no_group]");
    expect(getGroupFilterValueLabel("g-child", GROUPS)).toBe("Production / Night shift");
    expect(getGroupFilterValueLabel("g-gone", GROUPS)).toBeNull();
    expect(isGroupFilterKeyword("my_groups")).toBe(true);
    expect(isGroupFilterKeyword("g-root")).toBe(false);
  });
});

describe("matchesGroupFilter", () => {
  it("matches everything without values", () => {
    expect(matchesGroupFilter(undefined, {})).toBe(true);
    expect(matchesGroupFilter(null, {})).toBe(true);
    expect(matchesGroupFilter([], { has_group: true })).toBe(true);
  });

  it("matches a group id the row is in (the subtree comes with group_ids)", () => {
    const item = { group_ids: ["g-root", "g-child"], has_group: true, in_my_groups: false };
    expect(matchesGroupFilter(["g-root"], item)).toBe(true);
    expect(matchesGroupFilter(["g-other"], item)).toBe(false);
  });

  it("matches my_groups by in_my_groups and none by the absence of any group", () => {
    expect(matchesGroupFilter(["my_groups"], { in_my_groups: true })).toBe(true);
    expect(matchesGroupFilter(["my_groups"], { in_my_groups: false, has_group: true })).toBe(false);
    expect(matchesGroupFilter(["none"], { has_group: false })).toBe(true);
    expect(matchesGroupFilter(["none"], {})).toBe(true);
    expect(matchesGroupFilter(["none"], { has_group: true })).toBe(false);
  });

  it("ORs the values", () => {
    const item = { group_ids: ["g-child"], has_group: true, in_my_groups: false };
    expect(matchesGroupFilter(["g-other", "none"], item)).toBe(false);
    expect(matchesGroupFilter(["g-other", "g-child"], item)).toBe(true);
  });

  it("shouldFilterModule applies it with the other filters", () => {
    const module = { id: "m", status: "backlog", group_ids: ["g-root"], has_group: true } as unknown as IModule;
    expect(shouldFilterModule(module, {}, { groups: ["g-root"] })).toBe(true);
    expect(shouldFilterModule(module, {}, { groups: ["g-other"] })).toBe(false);
    expect(shouldFilterModule(module, {}, { groups: ["g-root"], status: ["completed"] })).toBe(false);
  });
});
