/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// local imports
import { findTotalDaysInRange, getDate, renderFormattedPayloadDate } from "../datetime";

/**
/**
 * Work item duration is measured in whole working days, inclusive of both the start and the finish date.
 * A work item that starts and finishes on the same day lasts 1 day, so the shortest valid duration is 1.
 *
 * Only the schedule endpoints (start and finish) take part. The due date (`target_date`) is a
 * deadline and is never read or written here.
 *
 * The project's weekend days (0 = Sunday ... 6 = Saturday, like `Date.getDay()`) are not counted:
 * - a range's duration is the number of working days in it, but at least 1, so a range made only of weekend days
 *   still lasts 1 day;
 * - the finish date of a duration is its Nth working day on or after the start date, and the start date is its Nth
 *   working day on or before the finish date, so a start or finish on a weekend day counts from the nearest working day;
 * - holidays are not modelled, only the weekly pattern.
 * Every function takes `weekendDays`; without it no day is skipped.
 *
 * Mirrors `apps/api/plane/utils/work_item_duration.py`. Keep both in sync.
 */
export const WORK_ITEM_DURATION_MIN = 1;

/**
 * The subset of work item fields that participate in duration synchronization.
 * Kept structural (instead of `Pick<TIssue, ...>`) so this module stays free of type-package coupling.
 */
export type TWorkItemDurationFields = {
  start_date?: string | null;
  finish_date?: string | null;
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
 * @description Working days from `startDate` to `finishDate`, both included; 0 when the range is backwards
 * @example countWorkingDays(new Date(2026, 10, 2), new Date(2026, 10, 9), [0, 6]) // 6 (Mon 2 to Mon 9 Nov)
 */
export const countWorkingDays = (startDate: Date, finishDate: Date, weekendDays: readonly number[] = []): number => {
  const off = getOffDays(weekendDays);
  const start = startOfCalendarDay(startDate);
  const total = findTotalDaysInRange(start, startOfCalendarDay(finishDate), true) ?? 0;
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
 * @description The `count`th working day on or before `finishDate` (`count` is at least 1)
 * @example subtractWorkingDays(new Date(2026, 10, 9), 2, [0, 6]) // Fri 6 Nov
 */
export const subtractWorkingDays = (finishDate: Date, count: number, weekendDays: readonly number[] = []): Date => {
  const off = getOffDays(weekendDays);
  let day = startOfCalendarDay(finishDate);
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
 * @description The date `offset` working days from `day`: later for a positive offset, earlier for a negative one.
 * The offset counts the working days passed on the way, so a Friday plus 1 is Monday; an offset of 0 is the day itself.
 * @example shiftWorkingDays(new Date(2026, 10, 6), 1, [0, 6]) // Mon 9 Nov
 */
export const shiftWorkingDays = (day: Date, offset: number, weekendDays: readonly number[] = []): Date => {
  if (offset === 0) return startOfCalendarDay(day);
  if (offset > 0) return addWorkingDays(shiftDays(day, 1), offset, weekendDays);
  return subtractWorkingDays(shiftDays(day, -1), -offset, weekendDays);
};

/** @description The day work that "starts" on `day` really begins: the first working day on or after it */
export const effectiveStart = (day: Date, weekendDays: readonly number[] = []): Date =>
  addWorkingDays(day, 1, weekendDays);

/** @description The day work that "finishes" on `day` really ended: the last working day on or before it */
export const effectiveFinish = (day: Date, weekendDays: readonly number[] = []): Date =>
  subtractWorkingDays(day, 1, weekendDays);

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
  finishDate: string | Date | null | undefined,
  weekendDays: readonly number[] = []
): number | undefined => {
  const start = getDate(startDate);
  const finish = getDate(finishDate);
  if (!start || !finish) return undefined;
  // A range in the wrong order keeps its calendar count, which is how callers tell it is invalid
  if (startOfCalendarDay(finish) < startOfCalendarDay(start)) return findTotalDaysInRange(start, finish, true);
  return Math.max(countWorkingDays(start, finish, weekendDays), WORK_ITEM_DURATION_MIN);
};

/**
 * @description Derives the finish date by treating the start date as the anchor
 * @returns {string | undefined} date in `yyyy-mm-dd` payload format
 * @example calculateFinishDateFromDuration("2026-01-01", 5) // "2026-01-05"
 */
export const calculateFinishDateFromDuration = (
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
 * @description Derives the start date by treating the finish date as the anchor
 * @returns {string | undefined} date in `yyyy-mm-dd` payload format
 * @example calculateStartDateFromDuration("2026-01-10", 3) // "2026-01-08"
 */
export const calculateStartDateFromDuration = (
  finishDate: string | Date | null | undefined,
  duration: number | null | undefined,
  weekendDays: readonly number[] = []
): string | undefined => {
  const normalizedDuration = normalizeWorkItemDuration(duration);
  const finish = getDate(finishDate);
  if (!finish || normalizedDuration === null) return undefined;
  return renderFormattedPayloadDate(subtractWorkingDays(finish, normalizedDuration, weekendDays));
};

/**
 * @description Keeps `duration`, `start_date` and `finish_date` consistent after a single user edit.
 *
 * Rules, in the order they are applied:
 * - Editing `duration`
 *   - cleared            -> dates are left untouched
 *   - start date present -> start date is the anchor, finish date is recalculated
 *   - only finish date   -> finish date is the anchor, start date is recalculated
 *   - no dates at all    -> duration is stored on its own
 * - Editing `start_date` / `finish_date`
 *   - both dates present and ordered -> duration is recalculated from the range
 *   - both dates present but ordered backwards -> nothing is derived. The caller must reject the
 *     edit (see `validateWorkItemSchedule`); no date is moved or cleared
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
  const finishDateChanged = "finish_date" in change;

  const startDate = (startDateChanged ? change.start_date : current.start_date) ?? null;
  const finishDate = (finishDateChanged ? change.finish_date : current.finish_date) ?? null;

  // Duration driven: the user typed a duration, so the dates follow it.
  if ("duration" in change) {
    const duration = normalizeWorkItemDuration(change.duration);
    result.duration = duration;
    if (duration === null) return result;

    if (startDate) {
      result.finish_date = calculateFinishDateFromDuration(startDate, duration, weekendDays) ?? null;
    } else if (finishDate) {
      result.start_date = calculateStartDateFromDuration(finishDate, duration, weekendDays) ?? null;
    }
    return result;
  }

  if (!startDateChanged && !finishDateChanged) return result;

  // Date driven: the user picked a date, so the duration follows the dates.
  if (startDate && finishDate) {
    // A range ordered backwards derives nothing: the caller rejects the edit instead of moving the other end.
    const nextDuration = calculateWorkItemDuration(startDate, finishDate, weekendDays);
    if (nextDuration !== undefined && nextDuration >= WORK_ITEM_DURATION_MIN) result.duration = nextDuration;
    return result;
  }

  const duration = normalizeWorkItemDuration(current.duration);
  if (duration === null) return result;

  // Only fill in a date that is still empty and that the user did not just clear.
  if (startDate && !finishDate && !finishDateChanged) {
    result.finish_date = calculateFinishDateFromDuration(startDate, duration, weekendDays) ?? null;
  } else if (finishDate && !startDate && !startDateChanged) {
    result.start_date = calculateStartDateFromDuration(finishDate, duration, weekendDays) ?? null;
  }

  return result;
};
