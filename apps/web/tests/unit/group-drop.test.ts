/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getGroupDropValue } from "@/helpers/group-drop";

// 2026-03-04 is a Wednesday, 2026-03-08 a Sunday
describe("getGroupDropValue", () => {
  it("moves a list property from the source group to the destination group", () => {
    expect(getGroupDropValue("labels", ["a", "b"], "a", "c")).toEqual(["b", "c"]);
    expect(getGroupDropValue("labels", ["a", "b"], "a", "None")).toEqual(["b"]);
  });

  it("sets or clears a single value", () => {
    expect(getGroupDropValue("priority", "low", "low", "high")).toBe("high");
    expect(getGroupDropValue("priority", "low", "low", "None")).toBeNull();
  });

  it("gives a dropped work item the day that stands for a time bucket, as a group and as a sub group", () => {
    expect(getGroupDropValue("target_date_bucket", "2026-01-01", "earlier", "today", "2026-03-04")).toBe("2026-03-04");
    expect(getGroupDropValue("finish_date_bucket", null, "no_date", "next_week", "2026-03-04")).toBe("2026-03-15");
    expect(getGroupDropValue("start_date_bucket", "2026-03-10", "next_week", "no_date", "2026-03-04")).toBeNull();
  });

  it("refuses a bucket that names no single day", () => {
    expect(getGroupDropValue("target_date_bucket", "2026-03-04", "today", "earlier", "2026-03-04")).toBeUndefined();
    expect(getGroupDropValue("target_date_bucket", "2026-03-04", "today", "later", "2026-03-04")).toBeUndefined();
  });

  it("refuses This week on the last day of the week", () => {
    expect(getGroupDropValue("target_date_bucket", null, "no_date", "this_week", "2026-03-08")).toBeUndefined();
    expect(getGroupDropValue("target_date_bucket", null, "no_date", "this_week", "2026-03-07")).toBe("2026-03-08");
  });
});
