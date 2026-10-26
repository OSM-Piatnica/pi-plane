/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueRelationTypes } from "@plane/types";
import { describe, expect, it } from "vitest";
import {
  filterEnabledRelationOptions,
  isRelationTypeEnabled,
  RELATION_TOGGLE_GROUPS,
} from "@/helpers/relation-type-toggles";

describe("isRelationTypeEnabled", () => {
  it("always allows blocking", () => {
    const off = {
      is_relation_schedule_enabled: false,
      is_relation_traceability_enabled: false,
      is_relation_relates_to_enabled: false,
      is_relation_duplicate_enabled: false,
    };
    expect(isRelationTypeEnabled(off, "blocked_by")).toBe(true);
    expect(isRelationTypeEnabled(off, "blocking")).toBe(true);
  });

  it("uses the defaults when the project has no flags", () => {
    expect(isRelationTypeEnabled(undefined, "relates_to")).toBe(true);
    expect(isRelationTypeEnabled({}, "duplicate")).toBe(true);
    expect(isRelationTypeEnabled({}, "start_before")).toBe(false);
    expect(isRelationTypeEnabled({}, "tested_by")).toBe(false);
  });

  it("follows the flag of the group a type belongs to, in both directions", () => {
    expect(isRelationTypeEnabled({ is_relation_schedule_enabled: true }, "finish_after")).toBe(true);
    expect(isRelationTypeEnabled({ is_relation_schedule_enabled: true }, "causes")).toBe(false);
    expect(isRelationTypeEnabled({ is_relation_traceability_enabled: true }, "implements")).toBe(true);
    expect(isRelationTypeEnabled({ is_relation_relates_to_enabled: false }, "relates_to")).toBe(false);
  });

  it("covers each type once", () => {
    const all = Object.values(RELATION_TOGGLE_GROUPS).flat();
    expect(new Set(all).size).toBe(all.length);
    expect(all).toHaveLength(16);
  });
});

describe("filterEnabledRelationOptions", () => {
  const options = (Object.values(RELATION_TOGGLE_GROUPS).flat() as TIssueRelationTypes[])
    .concat(["blocked_by", "blocking"])
    .map((key) => ({ key }));
  const keys = (project: Parameters<typeof filterEnabledRelationOptions>[1]) =>
    filterEnabledRelationOptions(options, project).map((option) => option.key);

  it("offers only blocking, relates to and duplicate for a project on the defaults", () => {
    expect(keys({})).toEqual(["relates_to", "duplicate", "blocked_by", "blocking"]);
  });

  it("adds a whole group when its flag is on", () => {
    const schedule = keys({ is_relation_schedule_enabled: true });
    expect(schedule).toEqual(expect.arrayContaining(RELATION_TOGGLE_GROUPS.is_relation_schedule_enabled));
    expect(schedule).not.toContain("implements");
    const traceability = keys({ is_relation_traceability_enabled: true });
    expect(traceability).toEqual(expect.arrayContaining(RELATION_TOGGLE_GROUPS.is_relation_traceability_enabled));
    expect(traceability).not.toContain("start_before");
  });

  it("drops a default-on type when its flag is off but never blocking", () => {
    const result = keys({ is_relation_relates_to_enabled: false, is_relation_duplicate_enabled: false });
    expect(result).toEqual(["blocked_by", "blocking"]);
  });

  it("keeps the order of the options it is given", () => {
    const all = keys({
      is_relation_schedule_enabled: true,
      is_relation_traceability_enabled: true,
    });
    expect(all).toEqual(options.map((option) => option.key));
  });
});
