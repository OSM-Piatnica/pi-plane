/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Time buckets for grouping work items by a date (start, due or finish date). "Today" is the calendar day of the
 * person; a week begins on the start of the week of the project being listed, else the workspace's. The API has the same rules in `apps/api/plane/utils/date_buckets.py`;
 * keep the two in step.
 */
export type TDateBucket = "earlier" | "today" | "this_week" | "next_week" | "later" | "no_date";

/** The current day: a Date (its local day) or a `yyyy-mm-dd` string, e.g. the day in the person's time zone. */
export type TBucketToday = Date | string;

/** In the order the groups are shown. */
export const DATE_BUCKETS: TDateBucket[] = ["earlier", "today", "this_week", "next_week", "later", "no_date"];

const DAY_MS = 86_400_000;

const toDayNumber = (year: number, month: number, day: number) => Math.floor(Date.UTC(year, month, day) / DAY_MS);

const parseDay = (value: string): number | null => {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? toDayNumber(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : null;
};

const toCurrentDay = (today: TBucketToday): number => {
  const parsed = typeof today === "string" ? parseDay(today) : null;
  if (parsed !== null) return parsed;
  const date = typeof today === "string" ? new Date() : today;
  return toDayNumber(date.getFullYear(), date.getMonth(), date.getDate());
};

/** Days of the week since Monday (0..6) of a day number. 1970-01-01 was a Thursday. */
const daysSinceMonday = (dayNumber: number) => (((dayNumber + 3) % 7) + 7) % 7;

/** The weekday (0 = Sunday ... 6 = Saturday, like `Date.getDay()`) of a day number. */
const weekdayOf = (dayNumber: number) => (daysSinceMonday(dayNumber) + 1) % 7;

/**
 * The first day of a week, numbered like `Date.getDay()` and the `start_of_the_week` of a project or workspace
 * (0 = Sunday, 1 = Monday ... 6 = Saturday). A project and a workspace start on Monday unless they say otherwise.
 */
export const DEFAULT_WEEK_START = 1;

/** The last day of the week a day is in, for a week that begins on `weekStart`. */
const endOfWeekOf = (dayNumber: number, weekStart: number) =>
  dayNumber + 6 - ((weekdayOf(dayNumber) - weekStart + 7) % 7);

/**
 * The bucket of a `yyyy-mm-dd` date.
 * @param date - The date, or nothing for a work item without it
 * @param today - The current day (a date or a `yyyy-mm-dd` string in the person's time zone), defaults to now
 * @param weekStart - The first day of the week of the project (else the workspace), see `DEFAULT_WEEK_START`
 */
export const getDateBucket = (
  date: string | null | undefined,
  today: TBucketToday = new Date(),
  weekStart: number = DEFAULT_WEEK_START
): TDateBucket => {
  if (!date) return "no_date";
  const day = parseDay(date);
  if (day === null) return "no_date";
  const current = toCurrentDay(today);
  if (day < current) return "earlier";
  if (day === current) return "today";
  const endOfWeek = endOfWeekOf(current, weekStart);
  if (day <= endOfWeek) return "this_week";
  if (day <= endOfWeek + 7) return "next_week";
  return "later";
};

const formatDayNumber = (dayNumber: number) => new Date(dayNumber * DAY_MS).toISOString().slice(0, 10);

/** Which end of a period a date belongs to: a start date goes to its first working day, other dates to its last. */
export type TDateBucketEdge = "start" | "end";

type TDropOptions = {
  /** Days that are no working days, numbered like `Date.getDay()` (0 = Sunday); none by default. */
  weekendDays?: readonly number[];
  /** A start date is dropped on the first working day of a period, any other date on the last one. */
  edge?: TDateBucketEdge;
  /** The first day of the week the buckets are counted by, see `DEFAULT_WEEK_START`. */
  weekStart?: number;
};

/** The first or last working day within the days `from..to`, or null when every day of them is a weekend day. */
const workingDayIn = (
  from: number,
  to: number,
  edge: TDateBucketEdge,
  weekendDays: readonly number[]
): number | null => {
  const weekend = new Set(weekendDays);
  for (let offset = 0; offset <= to - from; offset++) {
    const day = edge === "start" ? from + offset : to - offset;
    if (!weekend.has(weekdayOf(day))) return day;
  }
  return null;
};

/**
 * The date a work item gets when it is dropped into a bucket: today, or a working day of this/next week (the last
 * one for a finish or due date, the first one for a start date, using the project's weekend days), and nothing for
 * "no_date". Earlier and later name no single day, and "this_week" has none when no working day is left after
 * today (the last day of the week, or a weekend), so they return undefined (not droppable).
 */
export const getDateBucketDropDate = (
  bucket: string,
  today: TBucketToday = new Date(),
  { weekendDays = [], edge = "end", weekStart = DEFAULT_WEEK_START }: TDropOptions = {}
): string | null | undefined => {
  const current = toCurrentDay(today);
  const endOfWeek = endOfWeekOf(current, weekStart);
  switch (bucket) {
    case "today":
      return formatDayNumber(current);
    case "this_week": {
      const day = workingDayIn(current + 1, endOfWeek, edge, weekendDays);
      return day === null ? undefined : formatDayNumber(day);
    }
    case "next_week": {
      // a week with only weekend days has no working day: fall back to its edge so a drop is always possible
      const day = workingDayIn(endOfWeek + 1, endOfWeek + 7, edge, weekendDays);
      return formatDayNumber(day ?? (edge === "start" ? endOfWeek + 1 : endOfWeek + 7));
    }
    case "no_date":
      return null;
    default:
      return undefined;
  }
};

/** The group by options that group by the time bucket of a date, and the date each one buckets. */
export const DATE_BUCKET_GROUP_BY_FIELDS = {
  start_date_bucket: "start_date",
  target_date_bucket: "target_date",
  finish_date_bucket: "finish_date",
} as const;

export type TDateBucketGroupBy = keyof typeof DATE_BUCKET_GROUP_BY_FIELDS;
export type TDateBucketField = (typeof DATE_BUCKET_GROUP_BY_FIELDS)[TDateBucketGroupBy];

/** Which end of a period a dropped work item gets: a start date the first working day, the others the last. */
export const getDateBucketEdge = (key: TDateBucketGroupBy): TDateBucketEdge =>
  DATE_BUCKET_GROUP_BY_FIELDS[key] === "start_date" ? "start" : "end";

/** Whether a group by option groups by the time bucket of a date. */
export const isDateBucketGroupBy = (key: string | null | undefined): key is TDateBucketGroupBy =>
  !!key && Object.hasOwn(DATE_BUCKET_GROUP_BY_FIELDS, key);
