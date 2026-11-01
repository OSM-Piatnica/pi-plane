/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TIssue } from "@plane/types";
import { getGroupedWorkItemIds } from "@/store/issue/helpers/base-issues-utils";

// 2026-03-04 is a Wednesday
const item = (id: string, date: string | null, field: "target_date" | "finish_date" = "target_date") =>
  ({ id, [field]: date, created_at: "2026-01-01T00:00:00Z" }) as unknown as TIssue;

describe("grouping work items by the time bucket of a date", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 2, 4, 12));
  });
  afterEach(() => vi.useRealTimers());

  it("groups by the bucket of the due date", () => {
    const grouped = getGroupedWorkItemIds(
      [item("past", "2026-03-01"), item("today", "2026-03-04"), item("soon", "2026-03-06"), item("undated", null)],
      "target_date_bucket"
    );

    expect(grouped).toEqual({ earlier: ["past"], today: ["today"], this_week: ["soon"], no_date: ["undated"] });
  });

  it("groups by the bucket of the finish date", () => {
    const grouped = getGroupedWorkItemIds(
      [item("a", "2026-03-10", "finish_date"), item("b", "2026-04-20", "finish_date")],
      "finish_date_bucket"
    );

    expect(grouped).toEqual({ next_week: ["a"], later: ["b"] });
  });
});
