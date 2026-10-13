/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// local imports
import { addDaysToDate, findTotalDaysInRange, renderFormattedPayloadDate } from "../datetime";

/**
 * Work item duration is measured in whole days, inclusive of both the start and the finish date.
 * A work item that starts and finishes on the same day lasts 1 day, so the shortest valid duration is 1.
 * Non-working days (weekends, holidays) are intentionally not excluded.
 *
 * Only the schedule endpoints (start and finish) take part. The due date (`target_date`) is a
 * deadline and is never read or written here.
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
  finishDate: string | Date | null | undefined
): number | undefined => {
  if (!startDate || !finishDate) return undefined;
  return findTotalDaysInRange(startDate, finishDate, true);
};

/**
 * @description Derives the finish date by treating the start date as the anchor
 * @returns {string | undefined} date in `yyyy-mm-dd` payload format
 * @example calculateFinishDateFromDuration("2026-01-01", 5) // "2026-01-05"
 */
export const calculateFinishDateFromDuration = (
  startDate: string | Date | null | undefined,
  duration: number | null | undefined
): string | undefined => {
  const normalizedDuration = normalizeWorkItemDuration(duration);
  if (!startDate || normalizedDuration === null) return undefined;
  return renderFormattedPayloadDate(addDaysToDate(startDate, normalizedDuration - 1));
};

/**
 * @description Derives the start date by treating the finish date as the anchor
 * @returns {string | undefined} date in `yyyy-mm-dd` payload format
 * @example calculateStartDateFromDuration("2026-01-10", 3) // "2026-01-08"
 */
export const calculateStartDateFromDuration = (
  finishDate: string | Date | null | undefined,
  duration: number | null | undefined
): string | undefined => {
  const normalizedDuration = normalizeWorkItemDuration(duration);
  if (!finishDate || normalizedDuration === null) return undefined;
  return renderFormattedPayloadDate(addDaysToDate(finishDate, -(normalizedDuration - 1)));
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
 * @returns the full patch to send, containing `change` plus every derived field
 */
export const reconcileWorkItemDuration = (
  current: TWorkItemDurationFields,
  change: Partial<TWorkItemDurationFields>
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
      result.finish_date = calculateFinishDateFromDuration(startDate, duration) ?? null;
    } else if (finishDate) {
      result.start_date = calculateStartDateFromDuration(finishDate, duration) ?? null;
    }
    return result;
  }

  if (!startDateChanged && !finishDateChanged) return result;

  // Date driven: the user picked a date, so the duration follows the dates.
  if (startDate && finishDate) {
    const nextDuration = calculateWorkItemDuration(startDate, finishDate);
    if (nextDuration !== undefined && nextDuration >= WORK_ITEM_DURATION_MIN) result.duration = nextDuration;
    return result;
  }

  const duration = normalizeWorkItemDuration(current.duration);
  if (duration === null) return result;

  // Only fill in a date that is still empty and that the user did not just clear.
  if (startDate && !finishDate && !finishDateChanged) {
    result.finish_date = calculateFinishDateFromDuration(startDate, duration) ?? null;
  } else if (finishDate && !startDate && !startDateChanged) {
    result.start_date = calculateStartDateFromDuration(finishDate, duration) ?? null;
  }

  return result;
};
