/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  isFinishAfterSatisfied,
  isFinishBeforeSatisfied,
  isStartAfterSatisfied,
  isStartBeforeSatisfied,
  isTimelineRelationSatisfied,
} from "../src/issue-relation-constraints";

describe("issue relation timeline constraints", () => {
  it("starts before allows equal and earlier starts", () => {
    expect(isStartBeforeSatisfied("2026-01-01", "2026-01-01")).toBe(true);
    expect(isStartBeforeSatisfied("2026-01-01", "2026-01-02")).toBe(true);
    expect(isStartBeforeSatisfied("2026-01-03", "2026-01-02")).toBe(false);
  });

  it("starts after requires related to have begun", () => {
    expect(isStartAfterSatisfied("2026-01-02", "2026-01-01")).toBe(true);
    expect(isStartAfterSatisfied("2026-01-01", "2026-01-01")).toBe(true);
    expect(isStartAfterSatisfied("2026-01-01", "2026-01-02")).toBe(false);
  });

  it("finishes before allows equal and earlier finishes", () => {
    expect(isFinishBeforeSatisfied("2026-02-01", "2026-02-01")).toBe(true);
    expect(isFinishBeforeSatisfied("2026-02-01", "2026-02-02")).toBe(true);
    expect(isFinishBeforeSatisfied("2026-02-03", "2026-02-02")).toBe(false);
  });

  it("finishes after requires related to be finished", () => {
    expect(isFinishAfterSatisfied("2026-02-02", "2026-02-01")).toBe(true);
    expect(isFinishAfterSatisfied("2026-02-01", "2026-02-01")).toBe(true);
    expect(isFinishAfterSatisfied("2026-02-01", "2026-02-02")).toBe(false);
  });

  it("treats missing dates as unconstrained", () => {
    expect(isStartBeforeSatisfied(null, "2026-01-01")).toBe(true);
    expect(isFinishAfterSatisfied(undefined, null)).toBe(true);
  });

  it("dispatches timeline relation checks", () => {
    const issue = { start_date: "2026-01-01", target_date: "2026-01-10" };
    const related = { start_date: "2026-01-02", target_date: "2026-01-12" };

    expect(isTimelineRelationSatisfied("start_before", issue, related)).toBe(true);
    expect(isTimelineRelationSatisfied("start_after", issue, related)).toBe(false);
    expect(isTimelineRelationSatisfied("finish_before", issue, related)).toBe(true);
    expect(isTimelineRelationSatisfied("finish_after", issue, related)).toBe(false);
  });
});

describe("lag and start-to-finish", () => {
  const blocker = { start_date: "2026-01-01", target_date: "2026-01-10" };

  it("finish-to-start asks for the day after, plus the lag", () => {
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: "2026-01-11" }, blocker)).toBe(true);
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: "2026-01-10" }, blocker)).toBe(false);
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: "2026-01-12" }, blocker, 2)).toBe(false);
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: "2026-01-13" }, blocker, 2)).toBe(true);
  });

  it("a lead lets the two overlap", () => {
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: "2026-01-10" }, blocker, -1)).toBe(true);
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: "2026-01-09" }, blocker, -1)).toBe(false);
  });

  it("the blocking side reads the same lag", () => {
    expect(isTimelineRelationSatisfied("blocking", blocker, { start_date: "2026-01-13" }, 2)).toBe(true);
    expect(isTimelineRelationSatisfied("blocking", blocker, { start_date: "2026-01-12" }, 2)).toBe(false);
  });

  it("start-to-start and finish-to-finish take a lag", () => {
    expect(isStartBeforeSatisfied("2026-01-01", "2026-01-03", 2)).toBe(true);
    expect(isStartBeforeSatisfied("2026-01-01", "2026-01-02", 2)).toBe(false);
    expect(isFinishBeforeSatisfied("2026-02-01", "2026-02-04", 3)).toBe(true);
    expect(isFinishAfterSatisfied("2026-02-02", "2026-02-01", 3)).toBe(false);
  });

  it("start-to-finish: the related item cannot finish before this one starts", () => {
    expect(
      isTimelineRelationSatisfied("start_before_finish", { start_date: "2026-01-10" }, { target_date: "2026-01-10" })
    ).toBe(true);
    expect(
      isTimelineRelationSatisfied("start_before_finish", { start_date: "2026-01-10" }, { target_date: "2026-01-09" })
    ).toBe(false);
    expect(
      isTimelineRelationSatisfied("finish_after_start", { target_date: "2026-01-09" }, { start_date: "2026-01-10" })
    ).toBe(false);
    expect(
      isTimelineRelationSatisfied("start_before_finish", { start_date: "2026-01-10" }, { target_date: "2026-01-11" }, 2)
    ).toBe(false);
  });

  it("a missing date lifts every constraint", () => {
    expect(isTimelineRelationSatisfied("start_before_finish", {}, { target_date: "2026-01-01" }, 5)).toBe(true);
    expect(isTimelineRelationSatisfied("blocked_by", { start_date: "2026-01-01" }, {}, 5)).toBe(true);
  });
});
