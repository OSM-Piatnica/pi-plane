/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Time buckets for grouping work items by a date (due or finish date). Weeks run Monday to Sunday and "today"
 * is the calendar day of the person. The API has the same rules in `apps/api/plane/utils/date_buckets.py`;
 * keep the two in step.
 */
export type TDateBucket = "earlier" | "today" | "this_week" | "next_week" | "later" | "none";

/** In the order the groups are shown. */
export const DATE_BUCKETS: TDateBucket[] = ["earlier", "today", "this_week", "next_week", "later", "none"];

const DAY_MS = 86_400_000;

const toDayNumber = (year: number, month: number, day: number) => Math.floor(Date.UTC(year, month, day) / DAY_MS);

const parseDay = (value: string): number | null => {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? toDayNumber(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : null;
};

/** Days of the week since Monday (0..6) of a day number. 1970-01-01 was a Thursday. */
const daysSinceMonday = (dayNumber: number) => (((dayNumber + 3) % 7) + 7) % 7;

/**
 * The bucket of a `yyyy-mm-dd` date.
 * @param date - The date, or nothing for a work item without it
 * @param today - The current day, defaults to now
 */
export const getDateBucket = (date: string | null | undefined, today: Date = new Date()): TDateBucket => {
  if (!date) return "none";
  const day = parseDay(date);
  if (day === null) return "none";
  const current = toDayNumber(today.getFullYear(), today.getMonth(), today.getDate());
  if (day < current) return "earlier";
  if (day === current) return "today";
  const endOfWeek = current + (6 - daysSinceMonday(current));
  if (day <= endOfWeek) return "this_week";
  if (day <= endOfWeek + 7) return "next_week";
  return "later";
};

const formatDayNumber = (dayNumber: number) => new Date(dayNumber * DAY_MS).toISOString().slice(0, 10);

/**
 * The date a work item gets when it is dropped into a bucket: today, or the last day of the week for this/next
 * week, and nothing for "none". Earlier and later name no single day, so they return undefined (not droppable).
 */
export const getDateBucketDropDate = (bucket: string, today: Date = new Date()): string | null | undefined => {
  const current = toDayNumber(today.getFullYear(), today.getMonth(), today.getDate());
  const endOfWeek = current + (6 - daysSinceMonday(current));
  switch (bucket) {
    case "today":
      return formatDayNumber(current);
    case "this_week":
      return formatDayNumber(endOfWeek);
    case "next_week":
      return formatDayNumber(endOfWeek + 7);
    case "none":
      return null;
    default:
      return undefined;
  }
};

/** Whether a group by option groups by the time bucket of a date. */
export const isDateBucketGroupBy = (
  key: string | null | undefined
): key is "target_date_bucket" | "finish_date_bucket" => key === "target_date_bucket" || key === "finish_date_bucket";
