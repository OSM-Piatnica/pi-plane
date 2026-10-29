/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  isBlockedBySatisfied,
  isFinishBeforeSatisfied,
  isStartBeforeFinishSatisfied,
  isStartBeforeSatisfied,
  isTimelineRelationSatisfied,
} from "../src/issue-relation-constraints";
import { effectiveFinish, effectiveStart, shiftWorkingDays } from "../src/work-item/duration";

const SAT_SUN = [6, 0];

// 2 November 2026 is a Monday
const day = (offset: number) => new Date(2026, 10, 2 + offset);
const FRI = day(4);
const SAT = day(5);
const SUN = day(6);
const NEXT_MON = day(7);
const NEXT_TUE = day(8);
const NEXT_WED = day(9);

describe("shiftWorkingDays", () => {
  it("counts the working days passed", () => {
    expect(shiftWorkingDays(FRI, 1, SAT_SUN)).toEqual(NEXT_MON);
    expect(shiftWorkingDays(FRI, 3, SAT_SUN)).toEqual(NEXT_WED);
    expect(shiftWorkingDays(SAT, 1, SAT_SUN)).toEqual(NEXT_MON);
    expect(shiftWorkingDays(NEXT_MON, -1, SAT_SUN)).toEqual(FRI);
    expect(shiftWorkingDays(SUN, -1, SAT_SUN)).toEqual(FRI);
  });

  it("returns the day itself for no shift, and plain addition without weekend days", () => {
    expect(shiftWorkingDays(SAT, 0, SAT_SUN)).toEqual(SAT);
    expect(shiftWorkingDays(FRI, 3)).toEqual(day(7));
    expect(shiftWorkingDays(FRI, -3, [])).toEqual(day(1));
  });

  it("makes a weekend start or finish stand for the nearest working day", () => {
    expect(effectiveStart(SAT, SAT_SUN)).toEqual(NEXT_MON);
    expect(effectiveStart(FRI, SAT_SUN)).toEqual(FRI);
    expect(effectiveFinish(SUN, SAT_SUN)).toEqual(FRI);
    expect(effectiveFinish(FRI, SAT_SUN)).toEqual(FRI);
  });
});

describe("blocked by, in working days", () => {
  it("lets the blocked item start on the working day after the blocker finishes", () => {
    expect(isBlockedBySatisfied(NEXT_MON, FRI, 0, SAT_SUN)).toBe(true);
    expect(isBlockedBySatisfied(FRI, FRI, 0, SAT_SUN)).toBe(false);
  });

  it("treats a start on the weekend as the next working day, and a finish on the weekend as the last one", () => {
    expect(isBlockedBySatisfied(SAT, FRI, 0, SAT_SUN)).toBe(true);
    expect(isBlockedBySatisfied(SUN, FRI, 0, SAT_SUN)).toBe(true);
    expect(isBlockedBySatisfied(NEXT_MON, SAT, 0, SAT_SUN)).toBe(true);
    expect(isBlockedBySatisfied(NEXT_MON, SUN, 0, SAT_SUN)).toBe(true);
  });

  it("counts a lag in working days and lets a lead share a day", () => {
    expect(isBlockedBySatisfied(NEXT_TUE, FRI, 2, SAT_SUN)).toBe(false);
    expect(isBlockedBySatisfied(NEXT_WED, FRI, 2, SAT_SUN)).toBe(true);
    expect(isBlockedBySatisfied(FRI, FRI, -1, SAT_SUN)).toBe(true);
    expect(isBlockedBySatisfied(day(3), FRI, -1, SAT_SUN)).toBe(false);
  });

  it("counts every day without weekend days", () => {
    expect(isBlockedBySatisfied(SAT, FRI, 0)).toBe(true);
    expect(isBlockedBySatisfied(FRI, FRI, 0)).toBe(false);
  });
});

describe("the other rules, in working days", () => {
  it("count a lag in working days", () => {
    expect(isStartBeforeSatisfied(FRI, NEXT_MON, 1, SAT_SUN)).toBe(true);
    expect(isStartBeforeSatisfied(FRI, FRI, 1, SAT_SUN)).toBe(false);
    expect(isFinishBeforeSatisfied(FRI, NEXT_MON, 1, SAT_SUN)).toBe(true);
    expect(isFinishBeforeSatisfied(FRI, NEXT_MON, 2, SAT_SUN)).toBe(false);
    expect(isStartBeforeFinishSatisfied(FRI, NEXT_MON, 1, SAT_SUN)).toBe(true);
    expect(isStartBeforeFinishSatisfied(FRI, NEXT_MON, 2, SAT_SUN)).toBe(false);
  });

  it("never block on a missing date", () => {
    expect(isBlockedBySatisfied(null, FRI, 0, SAT_SUN)).toBe(true);
    expect(isStartBeforeSatisfied(FRI, null, 0, SAT_SUN)).toBe(true);
  });
});

describe("which calendar applies", () => {
  it("uses the weekend days of the work item the rule limits", () => {
    const blocker = { start_date: null, finish_date: FRI };
    // blocked_by limits the issue: its own days decide, not the blocker's
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: FRI }, blocker, 0, [], SAT_SUN)).toBe(false);
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: SAT }, blocker, 0, [0], SAT_SUN)).toBe(true);
    // blocking limits the related item
    expect(isTimelineRelationSatisfied("blocking", blocker, { start_date: SAT }, 0, SAT_SUN, [0])).toBe(true);
    expect(isTimelineRelationSatisfied("blocking", blocker, { start_date: FRI }, 0, SAT_SUN, [])).toBe(false);
  });
});
