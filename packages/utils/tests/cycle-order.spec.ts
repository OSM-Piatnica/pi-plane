/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { ICycle } from "@plane/types";
import { orderCyclesWithCompleted } from "../src/cycle";

const cycle = (id: string, status: string, start_date: string | null = null): ICycle =>
  ({ id, name: id, status, start_date, sort_order: 0 }) as unknown as ICycle;

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
