/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { ALL_ISSUES, DEFAULT_MODULE_ORDER_BY, DEFAULT_WORK_ITEM_ORDER_BY } from "@plane/constants";
import type { TIssue } from "@plane/types";
import { getGroupedWorkItemIds, getOrderedWorkItems } from "@/store/issue/helpers/base-issues-utils";

const workItem = (id: string, created_at: string) => ({ id, created_at }) as unknown as TIssue;

const WORK_ITEMS = [
  workItem("newest", "2026-03-01T00:00:00Z"),
  workItem("oldest", "2026-01-01T00:00:00Z"),
  workItem("middle", "2026-02-01T00:00:00Z"),
];

describe("default sort orders", () => {
  it("start with the newest work item or module last, as separate settings", () => {
    expect(DEFAULT_WORK_ITEM_ORDER_BY).toBe("created_at");
    expect(DEFAULT_MODULE_ORDER_BY).toBe("created_at");
  });

  it("orders work items oldest first for the default and newest first for the descending option", () => {
    expect(getOrderedWorkItems(WORK_ITEMS, "created_at")).toEqual(["oldest", "middle", "newest"]);
    expect(getOrderedWorkItems(WORK_ITEMS, "-created_at")).toEqual(["newest", "middle", "oldest"]);
  });

  it("groups ungrouped work items in the default order", () => {
    expect(getGroupedWorkItemIds(WORK_ITEMS)[ALL_ISSUES]).toEqual(["oldest", "middle", "newest"]);
  });
});
