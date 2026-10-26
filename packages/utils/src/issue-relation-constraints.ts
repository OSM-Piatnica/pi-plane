/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Mirror of `plane/utils/issue_relation_constraints.py`. Both sides have to answer the same
 * question the same way, so any rule changed here has to be changed there too.
 */

import { effectiveFinish, effectiveStart, shiftWorkingDays } from "./work-item/duration";

export type TTimelineRelationType =
  | "blocked_by"
  | "blocking"
  | "start_before"
  | "start_after"
  | "finish_before"
  | "finish_after"
  | "start_before_finish"
  | "finish_after_start";

export const TIMELINE_RELATION_TYPES: TTimelineRelationType[] = [
  "blocked_by",
  "blocking",
  "start_before",
  "start_after",
  "finish_before",
  "finish_after",
  "start_before_finish",
  "finish_after_start",
];

/** Largest lag, or lead when negative, a relation may carry, in working days; same bound as the API */
export const MAX_RELATION_LAG_DAYS = 3650;

export type TWorkItemTimelineDates = {
  start_date?: string | Date | null;
  target_date?: string | Date | null;
};

const toDate = (value: string | Date | null | undefined): Date | null => {
  if (value == null || value === "") return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : new Date(value.getFullYear(), value.getMonth(), value.getDate());
  }
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
};

type TDateValue = string | Date | null | undefined;

/** A start date as the day work really begins: a start on a weekend day begins on the next working day. */
const startOf = (value: TDateValue, weekendDays: readonly number[]): Date | null => {
  const date = toDate(value);
  return date ? effectiveStart(date, weekendDays) : null;
};

/** A finish date as the day work really ended: a finish on a weekend day ended on the last working day. */
const finishOf = (value: TDateValue, weekendDays: readonly number[]): Date | null => {
  const date = toDate(value);
  return date ? effectiveFinish(date, weekendDays) : null;
};

const shifted = (value: Date | null, days: number, weekendDays: readonly number[]): Date | null =>
  value ? shiftWorkingDays(value, days, weekendDays) : null;

const isOnOrBefore = (left: Date | null, right: Date | null): boolean => {
  if (!left || !right) return true;
  return left.getTime() <= right.getTime();
};

/**
 * Start-to-start: the related work item starts at least `lag` working days after this one (0 = on or after).
 * `weekendDays` are those of the work item that comes later, the one whose dates the rule limits.
 */
export const isStartBeforeSatisfied = (
  issueStart: TDateValue,
  relatedStart: TDateValue,
  lag = 0,
  weekendDays: readonly number[] = []
): boolean =>
  isOnOrBefore(shifted(startOf(issueStart, weekendDays), lag, weekendDays), startOf(relatedStart, weekendDays));

export const isStartAfterSatisfied = (
  issueStart: TDateValue,
  relatedStart: TDateValue,
  lag = 0,
  weekendDays: readonly number[] = []
): boolean => isStartBeforeSatisfied(relatedStart, issueStart, lag, weekendDays);

/** Finish-to-finish: the related work item finishes at least `lag` working days after this one. */
export const isFinishBeforeSatisfied = (
  issueFinish: TDateValue,
  relatedFinish: TDateValue,
  lag = 0,
  weekendDays: readonly number[] = []
): boolean =>
  isOnOrBefore(shifted(finishOf(issueFinish, weekendDays), lag, weekendDays), finishOf(relatedFinish, weekendDays));

export const isFinishAfterSatisfied = (
  issueFinish: TDateValue,
  relatedFinish: TDateValue,
  lag = 0,
  weekendDays: readonly number[] = []
): boolean => isFinishBeforeSatisfied(relatedFinish, issueFinish, lag, weekendDays);

/** Start-to-finish: the related work item cannot finish before `lag` working days after this one has started. */
export const isStartBeforeFinishSatisfied = (
  issueStart: TDateValue,
  relatedFinish: TDateValue,
  lag = 0,
  weekendDays: readonly number[] = []
): boolean =>
  isOnOrBefore(shifted(startOf(issueStart, weekendDays), lag, weekendDays), finishOf(relatedFinish, weekendDays));

export const isFinishAfterStartSatisfied = (
  issueFinish: TDateValue,
  relatedStart: TDateValue,
  lag = 0,
  weekendDays: readonly number[] = []
): boolean => isStartBeforeFinishSatisfied(relatedStart, issueFinish, lag, weekendDays);

/**
 * Finish-to-start: the blocker has to be done before the blocked work item starts.
 *
 * Both dates are inclusive days, so a blocker finishing on the day the blocked item starts still overlaps it: with
 * no lag the blocked item starts on the working day after the blocker finishes (a Friday finish lets the next item
 * start on Monday), a lag of 2 asks for two free working days in between, and a lead of -1 lets them share a day.
 * `weekendDays` are those of the blocked work item.
 */
export const isBlockedBySatisfied = (
  issueStart: TDateValue,
  blockerFinish: TDateValue,
  lag = 0,
  weekendDays: readonly number[] = []
): boolean => {
  const start = startOf(issueStart, weekendDays);
  const finish = finishOf(blockerFinish, weekendDays);
  if (!start || !finish) return true;
  return shiftWorkingDays(finish, lag + 1, weekendDays).getTime() <= start.getTime();
};

/** Which work item a timeline rule limits, the one that comes later. */
export const getDependentSide = (relationType: TTimelineRelationType): "issue" | "related" =>
  relationType === "blocked_by" ||
  relationType === "start_after" ||
  relationType === "finish_after" ||
  relationType === "finish_after_start"
    ? "issue"
    : "related";

/**
 * Whether the dates meet the rule of the relation. Working days are counted with the weekend days of the work item
 * the rule limits (the dependent one), so a rule between two projects uses the calendar of the one that has to move.
 */
export const isTimelineRelationSatisfied = (
  relationType: TTimelineRelationType,
  issueDates: TWorkItemTimelineDates,
  relatedDates: TWorkItemTimelineDates,
  lag = 0,
  issueWeekendDays: readonly number[] = [],
  relatedWeekendDays: readonly number[] = []
): boolean => {
  const weekendDays = getDependentSide(relationType) === "issue" ? issueWeekendDays : relatedWeekendDays;
  switch (relationType) {
    case "blocked_by":
      return isBlockedBySatisfied(issueDates.start_date, relatedDates.target_date, lag, weekendDays);
    case "blocking":
      return isBlockedBySatisfied(relatedDates.start_date, issueDates.target_date, lag, weekendDays);
    case "start_before":
      return isStartBeforeSatisfied(issueDates.start_date, relatedDates.start_date, lag, weekendDays);
    case "start_after":
      return isStartAfterSatisfied(issueDates.start_date, relatedDates.start_date, lag, weekendDays);
    case "finish_before":
      return isFinishBeforeSatisfied(issueDates.target_date, relatedDates.target_date, lag, weekendDays);
    case "finish_after":
      return isFinishAfterSatisfied(issueDates.target_date, relatedDates.target_date, lag, weekendDays);
    case "start_before_finish":
      return isStartBeforeFinishSatisfied(issueDates.start_date, relatedDates.target_date, lag, weekendDays);
    case "finish_after_start":
      return isFinishAfterStartSatisfied(issueDates.target_date, relatedDates.start_date, lag, weekendDays);
    default: {
      const _exhaustive: never = relationType;
      return _exhaustive;
    }
  }
};
