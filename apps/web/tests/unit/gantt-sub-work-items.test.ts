/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { flattenGanttRows } from "../../helpers/gantt-sub-work-items.helper";

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
