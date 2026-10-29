/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it, vi } from "vitest";
import type { IGanttBlock } from "@plane/types";
import { getSiblingDrop, getSortOrderAt, handleSiblingOrderChange } from "../../components/gantt-chart/sidebar/utils";

// rows as rendered: a (a1, a2 (a2x)), b, c
const blockIds = ["a", "a1", "a2", "a2x", "b", "c"];
const parents: Record<string, string | null> = { a: null, a1: "a", a2: "a", a2x: "a2", b: null, c: null };
const getParentId = (id: string) => parents[id];
const drop = (draggingBlockId: string, droppedBlockId: string, dropAtEndOfList = false) =>
  getSiblingDrop({ blockIds, draggingBlockId, droppedBlockId, dropAtEndOfList, getParentId });

describe("getSiblingDrop", () => {
  it("moves a top-level row above another top-level row", () => {
    expect(drop("c", "b")).toEqual({ siblingIds: ["a", "b"], index: 1, sourceIndex: 2 });
  });

  it("moves a row to the end of the top level", () => {
    expect(drop("a", "c", true)).toEqual({ siblingIds: ["b", "c"], index: 2, sourceIndex: 0 });
  });

  it("lands a top-level row after a parent whose subtree ends at the gap", () => {
    // the gap above b closes a's subtree: c moves between a and b
    expect(drop("c", "b")?.index).toBe(1);
    // dropping above a2x (a child of a2) is not a gap between top-level rows
    expect(drop("c", "a2x")).toBeUndefined();
  });

  it("reorders sub-work items among their siblings", () => {
    expect(drop("a2", "a1")).toEqual({ siblingIds: ["a1"], index: 0, sourceIndex: 1 });
    expect(drop("a1", "b")).toEqual({ siblingIds: ["a2"], index: 1, sourceIndex: 0 });
  });

  it("ignores a drop under another parent", () => {
    expect(drop("a1", "c")).toBeUndefined();
    expect(drop("a1", "a2x")).toBeUndefined();
    expect(drop("b", "a1")).toBeUndefined();
    expect(drop("a2x", "a1")).toBeUndefined();
  });

  it("ignores a drop that leaves the row where it is", () => {
    expect(drop("a1", "a2")).toBeUndefined();
    expect(drop("b", "c")).toBeUndefined();
    expect(drop("c", "c", true)).toBeUndefined();
  });

  it("treats a flat list as one group of siblings", () => {
    expect(
      getSiblingDrop({ blockIds: ["x", "y", "z"], draggingBlockId: "z", droppedBlockId: "x", dropAtEndOfList: false })
    ).toEqual({ siblingIds: ["x", "y"], index: 0, sourceIndex: 2 });
  });

  it("does not loop on a parent cycle", () => {
    const cyclic: Record<string, string> = { p: "q", q: "p" };
    expect(
      getSiblingDrop({
        blockIds: ["p", "q"],
        draggingBlockId: "p",
        droppedBlockId: "q",
        dropAtEndOfList: false,
        getParentId: (id) => cyclic[id],
      })
    ).toBeUndefined();
  });
});

const sortOrder = (id: string) => ({ a: 1000, b: 2000, c: 4000 })[id] ?? 0;

describe("getSortOrderAt", () => {
  it("is below the first, above the last and between two", () => {
    expect(getSortOrderAt(["a", "b"], 0, sortOrder)).toBe(0);
    expect(getSortOrderAt(["a", "b"], 2, sortOrder)).toBe(3000);
    expect(getSortOrderAt(["a", "c"], 1, sortOrder)).toBe(2500);
  });

  it("has nothing to go by without siblings", () => {
    expect(getSortOrderAt([], 0, sortOrder)).toBeUndefined();
  });
});

describe("handleSiblingOrderChange", () => {
  const sortOrders: Record<string, number> = { a: 1000, a1: 10, a2: 20, a2x: 5, b: 2000, c: 3000 };
  const getBlockById = (id: string) => ({ id, data: { id }, sort_order: sortOrders[id] }) as unknown as IGanttBlock;

  it("sends the new sort order and the positions among the siblings", () => {
    const update = vi.fn();
    handleSiblingOrderChange(
      { blockIds, draggingBlockId: "a2", droppedBlockId: "a1", dropAtEndOfList: false, getParentId },
      getBlockById,
      update
    );
    expect(update).toHaveBeenCalledWith(
      { id: "a2" },
      { sort_order: { destinationIndex: 0, newSortOrder: -990, sourceIndex: 1 } }
    );
  });

  it("sends nothing for a drop that is not allowed", () => {
    const update = vi.fn();
    handleSiblingOrderChange(
      { blockIds, draggingBlockId: "a1", droppedBlockId: "c", dropAtEndOfList: false, getParentId },
      getBlockById,
      update
    );
    expect(update).not.toHaveBeenCalled();
  });
});
