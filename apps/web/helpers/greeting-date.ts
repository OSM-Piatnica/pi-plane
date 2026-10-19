/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * The weekday, short date and 24-hour clock of the home page greeting, in the user's language
 * (`intlLocale` is a BCP 47 tag such as "en-US" or "pl"). English gives "Monday", "Oct 19" and "14:05".
 */
export const formatGreetingDate = (intlLocale: string, date: Date, timeZone?: string) => ({
  weekDay: new Intl.DateTimeFormat(intlLocale, { weekday: "long" }).format(date),
  date: new Intl.DateTimeFormat(intlLocale, { month: "short", day: "numeric" }).format(date),
  time: new Intl.DateTimeFormat(intlLocale, {
    timeZone,
    hourCycle: "h23",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date),
});
