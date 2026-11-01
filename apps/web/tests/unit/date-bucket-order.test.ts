/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getDateBucketOrderBy } from "@/helpers/date-bucket-order";

describe("getDateBucketOrderBy", () => {
  it("orders by the grouped date when a list in the default order is grouped by a date bucket", () => {
    expect(
      getDateBucketOrderBy(
        { group_by: "target_date_bucket" },
        { group_by: "target_date_bucket", order_by: "created_at" }
      )
    ).toBe("target_date");
    expect(getDateBucketOrderBy({ group_by: "finish_date_bucket" }, { group_by: "finish_date_bucket" })).toBe(
      "finish_date"
    );
    expect(getDateBucketOrderBy({ group_by: "start_date_bucket" }, { order_by: "created_at" })).toBe("start_date");
  });

  it("keeps an order the person chose", () => {
    expect(getDateBucketOrderBy({ group_by: "target_date_bucket" }, { order_by: "-priority" })).toBeUndefined();
    expect(getDateBucketOrderBy({ group_by: "target_date_bucket" }, { order_by: "sort_order" })).toBeUndefined();
  });

  it("keeps the order picked in the same update", () => {
    expect(
      getDateBucketOrderBy({ group_by: "target_date_bucket", order_by: "name" }, { order_by: "name" })
    ).toBeUndefined();
  });

  it("does nothing for other updates", () => {
    expect(getDateBucketOrderBy({ group_by: "priority" }, { order_by: "created_at" })).toBeUndefined();
    expect(getDateBucketOrderBy({ layout: "list" }, { group_by: "target_date_bucket" })).toBeUndefined();
    expect(getDateBucketOrderBy({ group_by: null }, { order_by: "created_at" })).toBeUndefined();
  });
});
