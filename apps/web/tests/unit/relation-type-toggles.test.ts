/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { isRelationTypeEnabled, RELATION_TOGGLE_GROUPS } from "@/helpers/relation-type-toggles";

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
