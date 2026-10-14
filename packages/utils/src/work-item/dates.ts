/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// local imports
import { reconcileWorkItemDuration } from "./duration";
import type { TWorkItemDurationFields } from "./duration";

/**
 * Planning dates of a work item.
 * - `start_date`  current planned first day of work
 * - `finish_date` current planned / forecast last day of work (schedule endpoint)
 * - `target_date` the due date: a deadline or commitment (name kept for API compatibility)
 *
 * All three are nullable and independent. The only invariant is `start_date <= finish_date`. Due is
 * never compared with start or finish. Mirrors `apps/api/plane/utils/work_item_dates.py`; the server
 * is authoritative, this module only previews what it will do.
 */
export type TWorkItemPlanningDates = TWorkItemDurationFields & {
  target_date?: string | null;
  /** The one-time "first finish/due entry fills both" opportunity has been used up. */
  dates_initialized?: boolean;
};

export const INITIALIZE_PAIRED_DATE_KEY = "initialize_paired_date";
export const FINISH_BEFORE_START_MESSAGE = "Finish must be on or after start.";

/** ISO `yyyy-mm-dd` strings sort chronologically, so no Date parsing (and no time zone) is involved. */
const day = (value: string | null | undefined): string | null => (value ? value.slice(0, 10) : null);

/**
 * @description Returns the validation message when the finish date precedes the start date.
 * Due dates are intentionally not part of this check.
 */
export const validateWorkItemSchedule = (
  startDate: string | null | undefined,
  finishDate: string | null | undefined
): string | undefined => {
  const start = day(startDate);
  const finish = day(finishDate);
  if (start && finish && finish < start) return FINISH_BEFORE_START_MESSAGE;
  return undefined;
};

export type TPairedDateNotice =
  | { code: "due_date_defaulted"; date: string }
  | { code: "finish_date_defaulted"; date: string }
  | { code: "finish_date_not_defaulted"; date: string };

export type TPlannedDateChange = {
  /** Patch to send: the user's change plus derived fields. Never contains the initialization flag unless requested. */
  patch: Partial<TWorkItemPlanningDates> & { initialize_paired_date?: boolean };
  /** Explains a defaulted (or deliberately not defaulted) paired date. */
  notice?: TPairedDateNotice;
  /** Set when the schedule would end before it starts; nothing must be saved. */
  error?: string;
};

/**
 * @description Whether the first manual finish/due entry may still fill the other field.
 * Requires that the one-time opportunity is unused and that the edit supplies exactly one of the two.
 */
export const canInitializePairedDate = (
  current: TWorkItemPlanningDates | undefined,
  change: Partial<TWorkItemPlanningDates>
): boolean => {
  if (current?.dates_initialized) return false;
  const finishIn = "finish_date" in change;
  const dueIn = "target_date" in change;
  return finishIn !== dueIn;
};

/**
 * @description Builds the patch for a single user edit of the planning dates, previewing the server
 * rules: duration follows start/finish, the schedule invariant is enforced, and (when `initialize`
 * is true and still allowed) the first finish or due entry fills the other field once.
 *
 * The preview is for display only. Never present it as saved; the server decides.
 *
 * @param initialize user wants the one-time default ("Set only finish/due" opts out)
 */
export const planWorkItemDateChange = (
  current: TWorkItemPlanningDates,
  change: Partial<TWorkItemPlanningDates>,
  initialize = true
): TPlannedDateChange => {
  let patch: TPlannedDateChange["patch"] = { ...change };
  let notice: TPairedDateNotice | undefined;

  const wantsPairing = initialize && canInitializePairedDate(current, change);
  if (wantsPairing) {
    patch[INITIALIZE_PAIRED_DATE_KEY] = true;
    if ("finish_date" in change) {
      const finish = day(change.finish_date);
      if (finish && !current.target_date) {
        patch.target_date = finish;
        notice = { code: "due_date_defaulted", date: finish };
      }
    } else {
      const due = day(change.target_date);
      if (due && !current.finish_date) {
        const start = day("start_date" in change ? change.start_date : current.start_date);
        if (start && due < start) {
          // Copying would manufacture an invalid schedule: keep the deadline alone and say so.
          notice = { code: "finish_date_not_defaulted", date: due };
        } else {
          patch.finish_date = due;
          notice = { code: "finish_date_defaulted", date: due };
        }
      }
    }
  }

  patch = { ...patch, ...reconcileWorkItemDuration(current, patch) };

  const error = validateWorkItemSchedule(
    "start_date" in patch ? patch.start_date : current.start_date,
    "finish_date" in patch ? patch.finish_date : current.finish_date
  );

  return { patch, notice, error };
};

/**
 * @description Today's calendar date (`yyyy-mm-dd`) in the given IANA time zone, falling back to the
 * runtime's own zone when none (or an invalid one) is given. Overdue and deadline boundaries are
 * defined in the project time zone (workspace time zone as fallback), never in UTC and never from
 * the viewer's own zone, so every viewer sees the same status. Date-only values are compared as
 * calendar days and are never converted through UTC midnight.
 * @param now injectable clock for tests
 */
export const getTodayInTimeZone = (timeZone?: string | null, now: Date = new Date()): string => {
  const format = (zone?: string) =>
    new Intl.DateTimeFormat("en-CA", { timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
  try {
    return format(timeZone || undefined);
  } catch {
    return format(undefined);
  }
};

export type TWorkItemDateStatuses = {
  /** Active, due exists and project-local today is after due. The due day itself is not overdue. */
  overdue: boolean;
  /** Active, finish and due exist, and finish is after due. Shown before the deadline passes. */
  forecastMissesDeadline: boolean;
  /** Active, due exists but finish does not. */
  forecastUnknown: boolean;
  /** Active and finish is before today. A schedule warning, not deadline overdue. */
  plannedFinishPassed: boolean;
  /** Completed on a project-local date after the due date that applied at completion. */
  completedLate: boolean;
};

/**
 * @description Derives the independent date-only statuses. All dates are `yyyy-mm-dd` calendar days;
 * `today` and `completedOn` must already be expressed in the project time zone (workspace time zone
 * as fallback). This function never reads a clock.
 */
export const getWorkItemDateStatuses = (args: {
  finishDate?: string | null;
  dueDate?: string | null;
  today: string;
  isActive: boolean;
  completedOn?: string | null;
  dueAtCompletion?: string | null;
}): TWorkItemDateStatuses => {
  const finish = day(args.finishDate);
  const due = day(args.dueDate);
  const today = day(args.today) as string;
  const completed = day(args.completedOn);
  const dueThen = day(args.dueAtCompletion);

  return {
    overdue: args.isActive && due !== null && today > due,
    forecastMissesDeadline: args.isActive && finish !== null && due !== null && finish > due,
    forecastUnknown: args.isActive && due !== null && finish === null,
    plannedFinishPassed: args.isActive && finish !== null && finish < today,
    completedLate: completed !== null && dueThen !== null && completed > dueThen,
  };
};
