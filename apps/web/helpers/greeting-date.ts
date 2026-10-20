/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type TGreetingPeriod = "morning" | "afternoon" | "evening";

// An unset or unknown time zone falls back to the browser's, because Intl throws a RangeError for it.
const resolveTimeZone = (timeZone?: string | null): string | undefined => {
  if (!timeZone) return undefined;
  try {
    new Intl.DateTimeFormat(undefined, { timeZone }).resolvedOptions();
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
    weekDay: new Intl.DateTimeFormat(intlLocale, { timeZone: zone, weekday: "long" }).format(date),
    date: new Intl.DateTimeFormat(intlLocale, { timeZone: zone, month: "short", day: "numeric" }).format(date),
    time: new Intl.DateTimeFormat(intlLocale, {
      timeZone: zone,
      hourCycle: "h23",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date),
    hour: Number(new Intl.DateTimeFormat("en-US", { timeZone: zone, hourCycle: "h23", hour: "2-digit" }).format(date)),
  };
};

export const getGreetingPeriod = (hour: number): TGreetingPeriod =>
  hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
