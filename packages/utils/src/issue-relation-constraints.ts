/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Mirror of `plane/utils/issue_relation_constraints.py`. Both sides have to answer the same
 * question the same way, so any rule changed here has to be changed there too.
 */

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

/** Largest lag, or lead when negative, a relation may carry; same bound as the API */
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

const addDays = (value: Date | null, days: number): Date | null => {
  if (!value) return null;
  return new Date(value.getFullYear(), value.getMonth(), value.getDate() + days);
};

const isOnOrBefore = (left: Date | null, right: Date | null): boolean => {
  if (!left || !right) return true;
  return left.getTime() <= right.getTime();
};

const isStrictlyBefore = (left: Date | null, right: Date | null): boolean => {
  if (!left || !right) return true;
  return left.getTime() < right.getTime();
};

type TDateValue = string | Date | null | undefined;

/** Start-to-start: the related work item starts at least `lag` days after this one (0 = on or after). */
export const isStartBeforeSatisfied = (issueStart: TDateValue, relatedStart: TDateValue, lag = 0): boolean =>
  isOnOrBefore(addDays(toDate(issueStart), lag), toDate(relatedStart));

export const isStartAfterSatisfied = (issueStart: TDateValue, relatedStart: TDateValue, lag = 0): boolean =>
  isStartBeforeSatisfied(relatedStart, issueStart, lag);

/** Finish-to-finish: the related work item finishes at least `lag` days after this one. */
export const isFinishBeforeSatisfied = (issueFinish: TDateValue, relatedFinish: TDateValue, lag = 0): boolean =>
  isOnOrBefore(addDays(toDate(issueFinish), lag), toDate(relatedFinish));

export const isFinishAfterSatisfied = (issueFinish: TDateValue, relatedFinish: TDateValue, lag = 0): boolean =>
  isFinishBeforeSatisfied(relatedFinish, issueFinish, lag);

/** Start-to-finish: the related work item cannot finish before `lag` days after this one has started. */
export const isStartBeforeFinishSatisfied = (issueStart: TDateValue, relatedFinish: TDateValue, lag = 0): boolean =>
  isOnOrBefore(addDays(toDate(issueStart), lag), toDate(relatedFinish));

export const isFinishAfterStartSatisfied = (issueFinish: TDateValue, relatedStart: TDateValue, lag = 0): boolean =>
  isStartBeforeFinishSatisfied(relatedStart, issueFinish, lag);

/**
 * Finish-to-start: the blocker has to be done before the blocked work item starts.
 *
 * Both dates are inclusive calendar days, so a blocker finishing on the day the blocked item
 * starts still overlaps it. Hence the strict comparison, unlike the start/finish pairs above:
 * with no lag the blocked item starts the day after the blocker finishes, a lag of 2 asks for two
 * free days in between, and a lead of -1 lets them share a day.
 */
export const isBlockedBySatisfied = (issueStart: TDateValue, blockerFinish: TDateValue, lag = 0): boolean =>
  isStrictlyBefore(addDays(toDate(blockerFinish), lag), toDate(issueStart));

export const isTimelineRelationSatisfied = (
  relationType: TTimelineRelationType,
  issueDates: TWorkItemTimelineDates,
  relatedDates: TWorkItemTimelineDates,
  lag = 0
): boolean => {
  switch (relationType) {
    case "blocked_by":
      return isBlockedBySatisfied(issueDates.start_date, relatedDates.target_date, lag);
    case "blocking":
      return isBlockedBySatisfied(relatedDates.start_date, issueDates.target_date, lag);
    case "start_before":
      return isStartBeforeSatisfied(issueDates.start_date, relatedDates.start_date, lag);
    case "start_after":
      return isStartAfterSatisfied(issueDates.start_date, relatedDates.start_date, lag);
    case "finish_before":
      return isFinishBeforeSatisfied(issueDates.target_date, relatedDates.target_date, lag);
    case "finish_after":
      return isFinishAfterSatisfied(issueDates.target_date, relatedDates.target_date, lag);
    case "start_before_finish":
      return isStartBeforeFinishSatisfied(issueDates.start_date, relatedDates.target_date, lag);
    case "finish_after_start":
      return isFinishAfterStartSatisfied(issueDates.target_date, relatedDates.start_date, lag);
    default: {
      const _exhaustive: never = relationType;
      return _exhaustive;
    }
  }
};
