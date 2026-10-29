/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getOffDayPositions } from "@/components/gantt-chart/helpers/off-day-positions";
import { DEFAULT_WEEKEND_DAYS, isWeekendDay, resolveWeekendDays } from "@/helpers/weekend-days";

describe("resolveWeekendDays", () => {
  it("uses the project's days inside a project, whatever the person picked", () => {
    expect(resolveWeekendDays({ profile: [1], project: { weekend_days: [5, 6] }, workspace: [0, 6] })).toEqual([5, 6]);
  });

  it("falls back to the workspace when the project has none", () => {
    expect(resolveWeekendDays({ project: {}, workspace: [5, 6] })).toEqual([5, 6]);
  });

  it("uses the person's own days outside a project", () => {
    expect(resolveWeekendDays({ profile: [1], workspace: [0, 6] })).toEqual([1]);
  });

  it("follows the workspace outside a project when the person has no list", () => {
    expect(resolveWeekendDays({ profile: null, workspace: [5, 6] })).toEqual([5, 6]);
  });

  it("keeps an empty list, meaning every day is a working day", () => {
    expect(resolveWeekendDays({ profile: [], workspace: [0, 6] })).toEqual([]);
    expect(resolveWeekendDays({ project: { weekend_days: [] }, workspace: [0, 6] })).toEqual([]);
  });

  it("ends on Saturday and Sunday when nothing is set", () => {
    expect(resolveWeekendDays({})).toEqual([...DEFAULT_WEEKEND_DAYS]);
  });
});

describe("isWeekendDay", () => {
  it("accepts a weekday number or a date", () => {
    expect(isWeekendDay(6, [5, 6])).toBe(true);
    expect(isWeekendDay(1, [5, 6])).toBe(false);
    // 2026-11-07 is a Saturday
    expect(isWeekendDay(new Date(2026, 10, 7), [5, 6])).toBe(true);
    expect(isWeekendDay(new Date(2026, 10, 9), [5, 6])).toBe(false);
  });
});

describe("getOffDayPositions", () => {
  // Monday 2026-11-02 to Sunday 2026-11-08
  const monday = new Date(2026, 10, 2);
  const sunday = new Date(2026, 10, 8);

  it("places each off day at its offset from the chart start", () => {
    expect(getOffDayPositions(monday, sunday, 60, [0, 6])).toEqual([5 * 60, 6 * 60]);
  });

  it("follows other days", () => {
    expect(getOffDayPositions(monday, sunday, 20, [5, 6])).toEqual([4 * 20, 5 * 20]);
  });

  it("is empty when no day is off", () => {
    expect(getOffDayPositions(monday, sunday, 60, [])).toEqual([]);
  });

  it("starts counting from the first day of the chart even when it is an off day", () => {
    expect(getOffDayPositions(sunday, new Date(2026, 10, 10), 10, [0])).toEqual([0]);
  });
});
