/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  addDaysToDate,
  buildCalendarPlacement,
  getCalendarDragPatch,
  getScheduledSpan,
} from "../../store/issue/helpers/calendar-layers";

describe("getScheduledSpan", () => {
  it("returns the start..finish span", () => {
    expect(getScheduledSpan({ start_date: "2026-03-02", finish_date: "2026-03-05" })).toEqual({
      start: "2026-03-02",
      end: "2026-03-05",
    });
  });
  it("uses a single marker for single-ended items and ignores due", () => {
    expect(getScheduledSpan({ start_date: "2026-03-02", target_date: "2026-03-30" })).toEqual({
      start: "2026-03-02",
      end: "2026-03-02",
    });
    expect(getScheduledSpan({ finish_date: "2026-03-05" })).toEqual({ start: "2026-03-05", end: "2026-03-05" });
    expect(getScheduledSpan({ target_date: "2026-03-30" })).toBeNull();
  });
});

describe("buildCalendarPlacement", () => {
  const items = [
    { id: "a", start_date: "2026-03-02", finish_date: "2026-03-04", target_date: "2026-03-20" },
    { id: "b", finish_date: "2026-03-03" },
    { id: "c", target_date: "2026-03-04" },
  ];
  it("places scheduled items across their span and never by due", () => {
    const placement = buildCalendarPlacement("scheduled", items, "2026-03-01", "2026-03-31");
    expect(placement).toEqual({
      "2026-03-02": ["a"],
      "2026-03-03": ["a", "b"],
      "2026-03-04": ["a"],
    });
  });
  it("clips spans to the visible range", () => {
    const placement = buildCalendarPlacement("scheduled", items, "2026-03-03", "2026-03-03");
    expect(placement).toEqual({ "2026-03-03": ["a", "b"] });
  });
  it("places deadline items on their due date only", () => {
    const placement = buildCalendarPlacement("deadlines", items, "2026-03-01", "2026-03-31");
    expect(placement).toEqual({ "2026-03-20": ["a"], "2026-03-04": ["c"] });
  });
});

describe("getCalendarDragPatch", () => {
  it("shifts start and finish by the same days in the scheduled layer without touching due", () => {
    const patch = getCalendarDragPatch(
      "scheduled",
      { start_date: "2026-03-30", finish_date: "2026-04-02", target_date: "2026-04-10" },
      "2026-03-31",
      "2026-04-03"
    );
    expect(patch).toEqual({ start_date: "2026-04-02", finish_date: "2026-04-05" });
  });
  it("moves a single-ended item", () => {
    expect(getCalendarDragPatch("scheduled", { finish_date: "2026-03-05" }, "2026-03-05", "2026-03-01")).toEqual({
      finish_date: "2026-03-01",
    });
  });
  it("changes only the due date in the deadlines layer", () => {
    expect(
      getCalendarDragPatch(
        "deadlines",
        { start_date: "2026-03-01", finish_date: "2026-03-05", target_date: "2026-03-10" },
        "2026-03-10",
        "2026-03-12"
      )
    ).toEqual({ target_date: "2026-03-12" });
  });
  it("returns null for a no-op drop", () => {
    expect(getCalendarDragPatch("scheduled", { start_date: "2026-03-01" }, "2026-03-01", "2026-03-01")).toBeNull();
  });
  it("adds days across month boundaries", () => {
    expect(addDaysToDate("2026-02-28", 2)).toBe("2026-03-02");
  });
});
