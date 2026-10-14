/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { ICycle } from "@plane/types";
import { orderCycles, orderCyclesWithCompleted, sortCyclesByOrderBy } from "../src/cycle";

const cycle = (id: string, status: string, start_date: string | null = null, sort_order = 0, name = id): ICycle =>
  ({ id, name, status, start_date, sort_order }) as unknown as ICycle;

describe("orderCyclesWithCompleted", () => {
  it("orders current, upcoming, draft, then completed by start date", () => {
    const result = orderCyclesWithCompleted([
      cycle("done-late", "COMPLETED", "2026-03-01"),
      cycle("draft", "DRAFT"),
      cycle("upcoming", "UPCOMING", "2026-12-01"),
      cycle("done-early", "COMPLETED", "2026-01-01"),
      cycle("current", "CURRENT", "2026-06-01"),
    ]);
    expect(result.map((c) => c.id)).toEqual(["current", "upcoming", "draft", "done-early", "done-late"]);
  });

  it("keeps cycles with an unknown status and handles empty input", () => {
    expect(orderCyclesWithCompleted([])).toEqual([]);
    expect(orderCyclesWithCompleted([cycle("x", "WEIRD")]).map((c) => c.id)).toEqual(["x"]);
  });
});

describe("cycle order_by", () => {
  const cycles = [
    cycle("a", "UPCOMING", "2026-05-01", 30, "Sprint 10"),
    cycle("b", "CURRENT", "2026-03-01", 10, "Sprint 2"),
    cycle("c", "COMPLETED", null, 20, "Sprint 1"),
    cycle("d", "DRAFT", "2026-04-01", 5, "Sprint 3"),
  ];
  const ids = (list: ICycle[]) => list.map((c) => c.id);

  it("sorts by name naturally, ascending and descending", () => {
    expect(ids(sortCyclesByOrderBy(cycles, "name"))).toEqual(["c", "b", "d", "a"]);
    expect(ids(sortCyclesByOrderBy(cycles, "-name"))).toEqual(["a", "d", "b", "c"]);
  });

  it("sorts by start date and keeps cycles without a start date last", () => {
    expect(ids(sortCyclesByOrderBy(cycles, "start_date"))).toEqual(["b", "d", "a", "c"]);
    expect(ids(sortCyclesByOrderBy(cycles, "-start_date"))).toEqual(["a", "d", "b", "c"]);
  });

  it("sorts manually by sort_order", () => {
    expect(ids(sortCyclesByOrderBy(cycles, "sort_order"))).toEqual(["d", "b", "c", "a"]);
  });

  it("orderCycles drops completed cycles and defaults to the status order", () => {
    expect(ids(orderCycles(cycles))).toEqual(["b", "a", "d"]);
    expect(ids(orderCycles(cycles, "name"))).toEqual(["b", "d", "a"]);
  });

  it("orderCyclesWithCompleted keeps every cycle for non-status orders", () => {
    expect(ids(orderCyclesWithCompleted(cycles, "name"))).toEqual(["c", "b", "d", "a"]);
  });
});
