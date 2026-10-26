/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// local imports
import { findTotalDaysInRange, getDate, renderFormattedPayloadDate } from "../datetime";

/**
 * Work item duration is measured in whole working days, inclusive of both the start and the target date.
 * A work item that starts and ends on the same day lasts 1 day, so the shortest valid duration is 1.
 *
 * The project's weekend days (0 = Sunday ... 6 = Saturday, like `Date.getDay()`) are not counted:
 * - a range's duration is the number of working days in it, but at least 1, so a range made only of weekend days
 *   still lasts 1 day;
 * - the target date of a duration is its Nth working day on or after the start date, and the start date is its Nth
 *   working day on or before the target date, so a start or target on a weekend day counts from the nearest working day;
 * - holidays are not modelled, only the weekly pattern.
 * Every function takes `weekendDays`; without it no day is skipped.
 */
export const WORK_ITEM_DURATION_MIN = 1;

/**
 * The subset of work item fields that participate in duration synchronization.
 * Kept structural (instead of `Pick<TIssue, ...>`) so this module stays free of type-package coupling.
 */
export type TWorkItemDurationFields = {
  start_date?: string | null;
  target_date?: string | null;
  duration?: number | null;
};

/** The weekend days as a set; a week with no working day is treated as one without weekend, never as a trap. */
const getOffDays = (weekendDays: readonly number[]): Set<number> => {
  const off = new Set(weekendDays.filter((day) => Number.isInteger(day) && day >= 0 && day <= 6));
  return off.size < 7 ? off : new Set();
};

/** Midnight of the calendar day, in local time, so adding days never drifts across a daylight-saving change. */
const startOfCalendarDay = (date: Date): Date => new Date(date.getFullYear(), date.getMonth(), date.getDate());

const shiftDays = (date: Date, days: number): Date =>
  new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);

/**
 * @description Working days from `startDate` to `targetDate`, both included; 0 when the range is backwards
 * @example countWorkingDays(new Date(2026, 10, 2), new Date(2026, 10, 9), [0, 6]) // 6 (Mon 2 to Mon 9 Nov)
 */
export const countWorkingDays = (startDate: Date, targetDate: Date, weekendDays: readonly number[] = []): number => {
  const off = getOffDays(weekendDays);
  const start = startOfCalendarDay(startDate);
  const total = findTotalDaysInRange(start, startOfCalendarDay(targetDate), true) ?? 0;
  if (total <= 0) return 0;
  const fullWeeks = Math.floor(total / 7);
  const extra = total % 7;
  const firstExtra = shiftDays(start, fullWeeks * 7);
  let count = fullWeeks * (7 - off.size);
  for (let offset = 0; offset < extra; offset++) {
    if (!off.has(shiftDays(firstExtra, offset).getDay())) count++;
  }
  return count;
};

/**
 * @description The `count`th working day on or after `startDate` (`count` is at least 1)
 * @example addWorkingDays(new Date(2026, 10, 6), 2, [0, 6]) // Mon 9 Nov, as Fri 6 is the first day and the weekend is skipped
 */
export const addWorkingDays = (startDate: Date, count: number, weekendDays: readonly number[] = []): Date => {
  const off = getOffDays(weekendDays);
  let day = startOfCalendarDay(startDate);
  while (off.has(day.getDay())) day = shiftDays(day, 1);
  const weeks = Math.floor((count - 1) / (7 - off.size));
  let remaining = (count - 1) % (7 - off.size);
  day = shiftDays(day, weeks * 7);
  while (remaining > 0) {
    day = shiftDays(day, 1);
    if (!off.has(day.getDay())) remaining--;
  }
  return day;
};

/**
 * @description The `count`th working day on or before `targetDate` (`count` is at least 1)
 * @example subtractWorkingDays(new Date(2026, 10, 9), 2, [0, 6]) // Fri 6 Nov
 */
export const subtractWorkingDays = (targetDate: Date, count: number, weekendDays: readonly number[] = []): Date => {
  const off = getOffDays(weekendDays);
  let day = startOfCalendarDay(targetDate);
  while (off.has(day.getDay())) day = shiftDays(day, -1);
  const weeks = Math.floor((count - 1) / (7 - off.size));
  let remaining = (count - 1) % (7 - off.size);
  day = shiftDays(day, -weeks * 7);
  while (remaining > 0) {
    day = shiftDays(day, -1);
    if (!off.has(day.getDay())) remaining--;
  }
  return day;
};

/**
 * @description Coerces any user or API supplied duration into a valid stored value
 * @returns {number | null} whole number of days >= WORK_ITEM_DURATION_MIN, or null when unset
 * @example normalizeWorkItemDuration(3.4) // 3
 * @example normalizeWorkItemDuration(0) // 1
 * @example normalizeWorkItemDuration(null) // null
 */
export const normalizeWorkItemDuration = (value: number | null | undefined): number | null => {
  if (value === null || value === undefined) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.max(Math.round(value), WORK_ITEM_DURATION_MIN);
};

/**
 * @description Derives the duration in days from a date range, counting both ends
 * @returns {number | undefined} undefined when either date is missing. May be <= 0 when the
 * dates are ordered incorrectly, which lets callers detect an invalid range.
 * @example calculateWorkItemDuration("2026-01-01", "2026-01-05") // 5
 * @example calculateWorkItemDuration("2026-01-01", "2026-01-01") // 1
 */
export const calculateWorkItemDuration = (
  startDate: string | Date | null | undefined,
  targetDate: string | Date | null | undefined,
  weekendDays: readonly number[] = []
): number | undefined => {
  const start = getDate(startDate);
  const target = getDate(targetDate);
  if (!start || !target) return undefined;
  // A range in the wrong order keeps its calendar count, which is how callers tell it is invalid
  if (startOfCalendarDay(target) < startOfCalendarDay(start)) return findTotalDaysInRange(start, target, true);
  return Math.max(countWorkingDays(start, target, weekendDays), WORK_ITEM_DURATION_MIN);
};

/**
 * @description Derives the target date by treating the start date as the anchor
 * @returns {string | undefined} date in `yyyy-mm-dd` payload format
 * @example calculateTargetDateFromDuration("2026-01-01", 5) // "2026-01-05"
 */
export const calculateTargetDateFromDuration = (
  startDate: string | Date | null | undefined,
  duration: number | null | undefined,
  weekendDays: readonly number[] = []
): string | undefined => {
  const normalizedDuration = normalizeWorkItemDuration(duration);
  const start = getDate(startDate);
  if (!start || normalizedDuration === null) return undefined;
  return renderFormattedPayloadDate(addWorkingDays(start, normalizedDuration, weekendDays));
};

/**
 * @description Derives the start date by treating the target date as the anchor
 * @returns {string | undefined} date in `yyyy-mm-dd` payload format
 * @example calculateStartDateFromDuration("2026-01-10", 3) // "2026-01-08"
 */
export const calculateStartDateFromDuration = (
  targetDate: string | Date | null | undefined,
  duration: number | null | undefined,
  weekendDays: readonly number[] = []
): string | undefined => {
  const normalizedDuration = normalizeWorkItemDuration(duration);
  const target = getDate(targetDate);
  if (!target || normalizedDuration === null) return undefined;
  return renderFormattedPayloadDate(subtractWorkingDays(target, normalizedDuration, weekendDays));
};

/**
 * @description Keeps `duration`, `start_date` and `target_date` consistent after a single user edit.
 *
 * Rules, in the order they are applied:
 * - Editing `duration`
 *   - cleared            -> dates are left untouched
 *   - start date present -> start date is the anchor, target date is recalculated
 *   - only target date   -> target date is the anchor, start date is recalculated
 *   - no dates at all    -> duration is stored on its own
 * - Editing `start_date` / `target_date`
 *   - both dates present -> duration is recalculated from the range
 *   - both dates present but ordered backwards -> the existing length is preserved and the date the
 *     user did not touch is shifted, so the payload stays valid instead of failing validation
 *   - only one date left and a duration exists -> the still empty date is derived from the duration,
 *     but a date the user explicitly cleared is never resurrected
 *   - both dates cleared -> duration survives as a standalone estimate
 *
 * @param current the work item state before the edit
 * @param change the fields the user just edited; presence of a key signals intent, including `null`
 * @param weekendDays the project's non-working days, 0 = Sunday ... 6 = Saturday
 * @returns the full patch to send, containing `change` plus every derived field
 */
export const reconcileWorkItemDuration = (
  current: TWorkItemDurationFields,
  change: Partial<TWorkItemDurationFields>,
  weekendDays: readonly number[] = []
): Partial<TWorkItemDurationFields> => {
  const result: Partial<TWorkItemDurationFields> = { ...change };

  const startDateChanged = "start_date" in change;
  const targetDateChanged = "target_date" in change;

  const startDate = (startDateChanged ? change.start_date : current.start_date) ?? null;
  const targetDate = (targetDateChanged ? change.target_date : current.target_date) ?? null;

  // Duration driven: the user typed a duration, so the dates follow it.
  if ("duration" in change) {
    const duration = normalizeWorkItemDuration(change.duration);
    result.duration = duration;
    if (duration === null) return result;

    if (startDate) {
      result.target_date = calculateTargetDateFromDuration(startDate, duration, weekendDays) ?? null;
    } else if (targetDate) {
      result.start_date = calculateStartDateFromDuration(targetDate, duration, weekendDays) ?? null;
    }
    return result;
  }

  if (!startDateChanged && !targetDateChanged) return result;

  // Date driven: the user picked a date, so the duration follows the dates.
  if (startDate && targetDate) {
    const nextDuration = calculateWorkItemDuration(startDate, targetDate, weekendDays);

    if (nextDuration !== undefined && nextDuration >= WORK_ITEM_DURATION_MIN) {
      result.duration = nextDuration;
      return result;
    }

    // The new range is ordered backwards. Keep the length the work item already had and move the
    // opposite end instead, so a slipped start date drags the target date along with it.
    const previousDuration =
      normalizeWorkItemDuration(current.duration) ??
      normalizeWorkItemDuration(calculateWorkItemDuration(current.start_date, current.target_date, weekendDays)) ??
      WORK_ITEM_DURATION_MIN;

    result.duration = previousDuration;
    if (startDateChanged) {
      result.target_date = calculateTargetDateFromDuration(startDate, previousDuration, weekendDays) ?? null;
    } else {
      result.start_date = calculateStartDateFromDuration(targetDate, previousDuration, weekendDays) ?? null;
    }
    return result;
  }

  const duration = normalizeWorkItemDuration(current.duration);
  if (duration === null) return result;

  // Only fill in a date that is still empty and that the user did not just clear.
  if (startDate && !targetDate && !targetDateChanged) {
    result.target_date = calculateTargetDateFromDuration(startDate, duration, weekendDays) ?? null;
  } else if (targetDate && !startDate && !startDateChanged) {
    result.start_date = calculateStartDateFromDuration(targetDate, duration, weekendDays) ?? null;
  }

  return result;
};
