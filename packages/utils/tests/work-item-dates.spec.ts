/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  FINISH_BEFORE_START_MESSAGE,
  getTodayInTimeZone,
  getWorkItemDateStatuses,
  planWorkItemDateChange,
  validateWorkItemSchedule,
} from "../src/work-item/dates";

const TODAY = "2026-10-10";

describe("planWorkItemDateChange", () => {
  it("first finish fills due once, start stays empty", () => {
    const { patch, notice } = planWorkItemDateChange({}, { finish_date: "2026-10-20" });
    expect(patch.finish_date).toBe("2026-10-20");
    expect(patch.target_date).toBe("2026-10-20");
    expect(patch.start_date).toBeUndefined();
    expect(patch.initialize_paired_date).toBe(true);
    expect(notice).toEqual({ code: "due_date_defaulted", date: "2026-10-20" });
  });

  it("first due fills finish", () => {
    const { patch } = planWorkItemDateChange({}, { target_date: "2026-10-23" });
    expect(patch).toMatchObject({ finish_date: "2026-10-23", target_date: "2026-10-23" });
  });

  it("opting out sets only the supplied date", () => {
    const { patch, notice } = planWorkItemDateChange({}, { finish_date: "2026-10-20" }, false);
    expect(patch.target_date).toBeUndefined();
    expect(patch.initialize_paired_date).toBeUndefined();
    expect(notice).toBeUndefined();
  });

  it("start-only edit does not consume the opportunity; a later finish still initializes both", () => {
    const startOnly = planWorkItemDateChange({}, { start_date: "2026-10-19" });
    expect(startOnly.patch.initialize_paired_date).toBeUndefined();
    const later = planWorkItemDateChange({ start_date: "2026-10-19" }, { finish_date: "2026-10-21" });
    expect(later.patch).toMatchObject({ finish_date: "2026-10-21", target_date: "2026-10-21", duration: 3 });
  });

  it("a first due before start is saved alone with an explanation", () => {
    const { patch, notice, error } = planWorkItemDateChange({ start_date: "2026-10-19" }, { target_date: "2026-10-12" });
    expect(patch.finish_date).toBeUndefined();
    expect(notice).toEqual({ code: "finish_date_not_defaulted", date: "2026-10-12" });
    expect(error).toBeUndefined();
  });

  it("equal dates are independent after the first entry", () => {
    const current = { finish_date: "2026-10-20", target_date: "2026-10-20", dates_initialized: true };
    expect(planWorkItemDateChange(current, { finish_date: "2026-10-22" }).patch.target_date).toBeUndefined();
    expect(planWorkItemDateChange(current, { target_date: "2026-10-23" }).patch.finish_date).toBeUndefined();
  });

  it("a deliberately cleared field is never refilled", () => {
    const current = { finish_date: "2026-10-20", dates_initialized: true };
    expect(planWorkItemDateChange(current, { finish_date: "2026-10-22" }).patch.target_date).toBeUndefined();
    expect(planWorkItemDateChange({ dates_initialized: true }, { target_date: "2026-10-23" }).patch.finish_date).toBe(
      undefined
    );
  });

  it("never overwrites an existing value", () => {
    const { patch } = planWorkItemDateChange({ target_date: "2026-10-01" }, { finish_date: "2026-10-20" });
    expect(patch.target_date).toBeUndefined();
  });

  it("supplying both bypasses copying", () => {
    const { patch, notice } = planWorkItemDateChange({}, { finish_date: "2026-10-20", target_date: null });
    expect(patch.target_date).toBeNull();
    expect(notice).toBeUndefined();
  });

  it("rejects finish before start without moving or clearing anything", () => {
    const { patch, error } = planWorkItemDateChange(
      { start_date: "2026-10-19", finish_date: "2026-10-21", dates_initialized: true },
      { finish_date: "2026-10-18" }
    );
    expect(error).toBe(FINISH_BEFORE_START_MESSAGE);
    expect(patch.start_date).toBeUndefined();
  });

  it("allows finish after due and due before start", () => {
    expect(planWorkItemDateChange({ target_date: "2026-10-20", dates_initialized: true }, { finish_date: "2026-10-22" }).error).toBeUndefined();
    expect(validateWorkItemSchedule("2026-10-20", "2026-10-20")).toBeUndefined();
  });
});

describe("getWorkItemDateStatuses", () => {
  const base = { today: TODAY, isActive: true };
  it("fresh item has no warnings", () => {
    expect(Object.values(getWorkItemDateStatuses(base)).some(Boolean)).toBe(false);
  });
  it("overdue after the due day only", () => {
    expect(getWorkItemDateStatuses({ ...base, dueDate: "2026-10-08" }).overdue).toBe(true);
    expect(getWorkItemDateStatuses({ ...base, dueDate: "2026-10-10" }).overdue).toBe(false);
  });
  it("planned finish passed is not overdue", () => {
    const s = getWorkItemDateStatuses({ ...base, finishDate: "2026-10-08", dueDate: "2026-10-20" });
    expect(s.plannedFinishPassed).toBe(true);
    expect(s.overdue).toBe(false);
  });
  it("forecast misses deadline before it passes; unknown without finish", () => {
    const s = getWorkItemDateStatuses({ ...base, finishDate: "2026-10-22", dueDate: "2026-10-20" });
    expect(s.forecastMissesDeadline).toBe(true);
    expect(s.overdue).toBe(false);
    expect(getWorkItemDateStatuses({ ...base, dueDate: "2026-10-20" }).forecastUnknown).toBe(true);
  });
  it("completed items lose active warnings but keep late-completion history", () => {
    const s = getWorkItemDateStatuses({
      ...base,
      isActive: false,
      dueDate: "2026-12-01",
      completedOn: "2026-10-09",
      dueAtCompletion: "2026-10-08",
    });
    expect(s.overdue).toBe(false);
    expect(s.completedLate).toBe(true);
  });
});

describe("getTodayInTimeZone", () => {
  // 2026-03-29 23:30 UTC: Europe/Warsaw already moved to DST (UTC+2) and is on the 30th; New York is still the 29th
  const now = new Date("2026-03-29T23:30:00Z");
  it("uses the given time zone, not UTC and not the viewer", () => {
    expect(getTodayInTimeZone("Europe/Warsaw", now)).toBe("2026-03-30");
    expect(getTodayInTimeZone("America/New_York", now)).toBe("2026-03-29");
    expect(getTodayInTimeZone("UTC", now)).toBe("2026-03-29");
  });
  it("falls back to the runtime zone for an invalid zone", () => {
    expect(getTodayInTimeZone("Not/AZone", now)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
