/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type TGreetingPeriod = "morning" | "afternoon" | "evening";

// The greeting is recomputed on every clock tick, and building an Intl formatter is slow, so each
// distinct one (locale and options) is built once and reused.
const formatters = new Map<string, Intl.DateTimeFormat>();
const getFormatter = (locale: string, options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat => {
  const key = `${locale}|${JSON.stringify(options)}`;
  let formatter = formatters.get(key);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat(locale, options);
    formatters.set(key, formatter);
  }
  return formatter;
};

// An unset or unknown time zone falls back to the browser's, because Intl throws a RangeError for it.
const resolveTimeZone = (timeZone?: string | null): string | undefined => {
  if (!timeZone) return undefined;
  try {
    getFormatter("en-US", { timeZone });
    return timeZone;
  } catch {
    return undefined;
  }
};

/**
 * The weekday, short date and 24-hour clock of the home page greeting, in the user's language
 * (`intlLocale` is a BCP 47 tag such as "en-US" or "pl"), plus the hour (0-23) that picks the greeting.
 * Everything is read in the user's time zone, so the greeting, the day and the clock always agree.
 * English gives "Monday", "Oct 19" and "14:05".
 */
export const formatGreetingDate = (intlLocale: string, date: Date, timeZone?: string | null) => {
  const zone = resolveTimeZone(timeZone);
  return {
    weekDay: getFormatter(intlLocale, { timeZone: zone, weekday: "long" }).format(date),
    date: getFormatter(intlLocale, { timeZone: zone, month: "short", day: "numeric" }).format(date),
    time: getFormatter(intlLocale, { timeZone: zone, hourCycle: "h23", hour: "2-digit", minute: "2-digit" }).format(
      date
    ),
    hour: Number(getFormatter("en-US", { timeZone: zone, hourCycle: "h23", hour: "2-digit" }).format(date)),
  };
};

export const getGreetingPeriod = (hour: number): TGreetingPeriod =>
  hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
