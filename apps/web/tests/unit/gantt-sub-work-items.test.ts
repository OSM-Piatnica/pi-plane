/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  DEFAULT_GANTT_EXPANSION,
  flattenGanttRows,
  isGanttRowExpanded,
  showGanttLevels,
  toggleGanttRow,
} from "../../helpers/gantt-sub-work-items.helper";

const children: Record<string, string[]> = { a: ["a1", "a2"], a1: ["a1x"], b: ["b1"] };
const getChildIds = (id: string) => children[id];

describe("flattenGanttRows", () => {
  it("keeps the listed order when nothing is expanded", () => {
    const { ids, levelById } = flattenGanttRows(["a", "b"], new Set(), getChildIds);
    expect(ids).toEqual(["a", "b"]);
    expect(levelById).toEqual({ a: 0, b: 0 });
  });

  it("puts the sub-work items right below their expanded parent", () => {
    const { ids, levelById } = flattenGanttRows(["a", "b"], new Set(["a"]), getChildIds);
    expect(ids).toEqual(["a", "a1", "a2", "b"]);
    expect(levelById).toEqual({ a: 0, a1: 1, a2: 1, b: 0 });
  });

  it("expands nested levels in depth-first order", () => {
    const { ids, levelById } = flattenGanttRows(["a"], new Set(["a", "a1"]), getChildIds);
    expect(ids).toEqual(["a", "a1", "a1x", "a2"]);
    expect(levelById.a1x).toBe(2);
  });

  it("does not repeat a work item that is already listed at the top level", () => {
    const { ids, levelById } = flattenGanttRows(["a", "a2"], new Set(["a"]), getChildIds);
    expect(ids).toEqual(["a", "a1", "a2"]);
    expect(levelById.a2).toBe(0);
  });

  it("does not loop on a parent cycle", () => {
    const cyclic: Record<string, string[]> = { x: ["y"], y: ["x"] };
    const { ids } = flattenGanttRows(["x"], new Set(["x", "y"]), (id) => cyclic[id]);
    expect(ids).toEqual(["x", "y"]);
  });

  it("ignores expanded ids whose sub-work items are not loaded yet", () => {
    const { ids } = flattenGanttRows(["a", "z"], new Set(["z"]), getChildIds);
    expect(ids).toEqual(["a", "z"]);
  });
});

describe("flattenGanttRows with an expansion rule", () => {
  const rule = (depth: number | null) => (id: string, level: number) =>
    isGanttRowExpanded(showGanttLevels(depth), id, level);

  it("shows only the top level for depth 1 and one more level per step", () => {
    expect(flattenGanttRows(["a", "b"], rule(1), getChildIds).ids).toEqual(["a", "b"]);
    expect(flattenGanttRows(["a", "b"], rule(2), getChildIds).ids).toEqual(["a", "a1", "a2", "b", "b1"]);
    expect(flattenGanttRows(["a", "b"], rule(3), getChildIds).ids).toEqual(["a", "a1", "a1x", "a2", "b", "b1"]);
  });

  it("shows every level for a depth of null", () => {
    expect(flattenGanttRows(["a"], rule(null), getChildIds).ids).toEqual(["a", "a1", "a1x", "a2"]);
  });

  it("reports the expanded rows and the expanded rows that are not loaded yet", () => {
    const loaded: Record<string, string[]> = { a: ["a1"] };
    const rows = flattenGanttRows(["a", "b"], rule(null), (id) => loaded[id]);
    expect(rows.ids).toEqual(["a", "a1", "b"]);
    expect(Array.from(rows.expandedIds).toSorted()).toEqual(["a", "a1", "b"]);
    // a1 and b are unfolded but nothing is known about their sub-work items
    expect(rows.unloadedExpandedIds).toEqual(["a1", "b"]);
  });
});

describe("expansion state", () => {
  it("starts with the top level only", () => {
    expect(isGanttRowExpanded(DEFAULT_GANTT_EXPANSION, "a", 0)).toBe(false);
  });

  it("lets a row folded or unfolded by hand win over the levels", () => {
    const opened = toggleGanttRow(DEFAULT_GANTT_EXPANSION, "a", false);
    expect(isGanttRowExpanded(opened, "a", 0)).toBe(true);
    expect(isGanttRowExpanded(opened, "b", 0)).toBe(false);
    const closed = toggleGanttRow(showGanttLevels(null), "a", true);
    expect(isGanttRowExpanded(closed, "a", 0)).toBe(false);
    expect(isGanttRowExpanded(closed, "b", 0)).toBe(true);
  });

  it("forgets the rows chosen by hand when levels are chosen", () => {
    const opened = toggleGanttRow(DEFAULT_GANTT_EXPANSION, "a", false);
    expect(showGanttLevels(1).overrides).toEqual({});
    expect(isGanttRowExpanded(showGanttLevels(1), "a", 0)).toBe(false);
    expect(opened.overrides).toEqual({ a: true });
  });
});
