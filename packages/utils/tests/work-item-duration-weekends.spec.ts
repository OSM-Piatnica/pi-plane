/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  addWorkingDays,
  calculateStartDateFromDuration,
  calculateFinishDateFromDuration,
  calculateWorkItemDuration,
  countWorkingDays,
  reconcileWorkItemDuration,
  subtractWorkingDays,
} from "../src/work-item/duration";

const SAT_SUN = [6, 0];
const FRI_SAT = [5, 6];

// 2 November 2026 is a Monday
const day = (offset: number) => new Date(2026, 10, 2 + offset);
const iso = (offset: number) => {
  const date = day(offset);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
};

describe("countWorkingDays", () => {
  it("counts a range inside a week and skips a weekend inside the range", () => {
    expect(countWorkingDays(day(0), day(2), SAT_SUN)).toBe(3);
    expect(countWorkingDays(day(4), day(7), SAT_SUN)).toBe(2);
    expect(countWorkingDays(day(0), day(7), SAT_SUN)).toBe(6);
    expect(countWorkingDays(day(0), day(13), SAT_SUN)).toBe(10);
  });

  it("follows other weekend days", () => {
    expect(countWorkingDays(day(0), day(6), FRI_SAT)).toBe(5);
    expect(countWorkingDays(day(0), day(6), [3])).toBe(6);
  });

  it("counts every day without weekend days, and nothing for a backwards range", () => {
    expect(countWorkingDays(day(0), day(6), [])).toBe(7);
    expect(countWorkingDays(day(0), day(6))).toBe(7);
    expect(countWorkingDays(day(3), day(0), SAT_SUN)).toBe(0);
  });
});

describe("addWorkingDays and subtractWorkingDays", () => {
  it("skip the weekend going forward", () => {
    expect(addWorkingDays(day(0), 3, SAT_SUN)).toEqual(day(2));
    expect(addWorkingDays(day(4), 2, SAT_SUN)).toEqual(day(7));
    expect(addWorkingDays(day(0), 5, SAT_SUN)).toEqual(day(4));
  });

  it("count from the next working day when the start is a weekend day", () => {
    expect(addWorkingDays(day(5), 1, SAT_SUN)).toEqual(day(7));
    expect(addWorkingDays(day(6), 2, SAT_SUN)).toEqual(day(8));
  });

  it("jump whole weeks for long durations", () => {
    expect(addWorkingDays(day(0), 11, SAT_SUN)).toEqual(day(14));
  });

  it("skip the weekend going back", () => {
    expect(subtractWorkingDays(day(2), 3, SAT_SUN)).toEqual(day(0));
    expect(subtractWorkingDays(day(7), 2, SAT_SUN)).toEqual(day(4));
    expect(subtractWorkingDays(day(6), 1, SAT_SUN)).toEqual(day(4));
  });

  it("agree with counting, out and back, for every start and length", () => {
    for (const weekend of [SAT_SUN, FRI_SAT, [3], []]) {
      for (let startOffset = 0; startOffset < 14; startOffset++) {
        for (let length = 1; length < 30; length++) {
          const target = addWorkingDays(day(startOffset), length, weekend);
          expect(countWorkingDays(day(startOffset), target, weekend)).toBe(length);
          expect(countWorkingDays(subtractWorkingDays(target, length, weekend), target, weekend)).toBe(length);
        }
      }
    }
  });

  it("does not loop forever when every day is a weekend day", () => {
    expect(addWorkingDays(day(0), 3, [0, 1, 2, 3, 4, 5, 6])).toEqual(day(2));
  });
});

describe("work item duration with weekend days", () => {
  it("counts working days, at least one", () => {
    expect(calculateWorkItemDuration(iso(0), iso(7), SAT_SUN)).toBe(6);
    expect(calculateWorkItemDuration(iso(5), iso(6), SAT_SUN)).toBe(1);
    expect(calculateWorkItemDuration(iso(0), iso(7))).toBe(8);
  });

  it("still reports a backwards range as one", () => {
    expect(calculateWorkItemDuration(iso(3), iso(0), SAT_SUN)).toBeLessThanOrEqual(0);
  });

  it("derives the finish and the start from a duration", () => {
    expect(calculateFinishDateFromDuration(iso(4), 2, SAT_SUN)).toBe(iso(7));
    expect(calculateStartDateFromDuration(iso(7), 2, SAT_SUN)).toBe(iso(4));
  });

  it("moves the finish over the weekend when the duration is edited", () => {
    expect(
      reconcileWorkItemDuration({ start_date: iso(4), finish_date: iso(4), duration: 1 }, { duration: 3 }, SAT_SUN)
    ).toEqual({ duration: 3, finish_date: iso(8) });
  });

  it("recounts working days when a date is edited", () => {
    expect(
      reconcileWorkItemDuration(
        { start_date: iso(0), finish_date: iso(2), duration: 3 },
        { finish_date: iso(9) },
        SAT_SUN
      )
    ).toEqual({ finish_date: iso(9), duration: 8 });
  });

  it("derives nothing when the start passes the finish; the caller rejects the edit", () => {
    expect(
      reconcileWorkItemDuration(
        { start_date: iso(0), finish_date: iso(2), duration: 3 },
        { start_date: iso(4) },
        SAT_SUN
      )
    ).toEqual({ start_date: iso(4) });
  });

  it("is unchanged for a project without a weekend", () => {
    expect(
      reconcileWorkItemDuration({ start_date: iso(4), finish_date: iso(4), duration: 1 }, { duration: 3 }, [])
    ).toEqual({ duration: 3, finish_date: iso(6) });
  });
});
