/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { DateRangeSelect as DateRangeSelectBlock, DateSelect as DateSelectBlock } from "@plane/blocks/property-select";
import type { DateRangeSelectProps, DateSelectProps } from "@plane/blocks/property-select";
// hooks
import { useCalendarLocale } from "@/hooks/use-calendar-locale";

// English keeps the app's usual "Jan 05, 2024"; other languages use date-fns' localized medium date ("5. Jan. 2024"),
// which puts the day, month and year in that language's order (the same rule as `useLocalizedDates`).
const ENGLISH_LOCALE_CODE = "en-US";
const LOCALIZED_DATE_TOKEN = "PP";

/** The trigger date style of a language: `undefined` keeps the blocks' English default. */
export const getDateSelectFormatToken = (localeCode: string | undefined) =>
  localeCode === ENGLISH_LOCALE_CODE ? undefined : LOCALIZED_DATE_TOKEN;

/**
 * Web bindings for the presentational date pickers: they fill in the `date-fns` locale of the
 * user's language and its date style, so the calendar and the date in the trigger label are not
 * English-only. A caller can still pass its own `locale` or `formatToken`.
 */
export function DateSelect(props: DateSelectProps) {
  const { dateFnsLocale } = useCalendarLocale();
  const formatToken = getDateSelectFormatToken(dateFnsLocale.code);
  return <DateSelectBlock locale={dateFnsLocale} formatToken={formatToken} {...props} />;
}

export function DateRangeSelect(props: DateRangeSelectProps) {
  const { dateFnsLocale } = useCalendarLocale();
  const formatToken = getDateSelectFormatToken(dateFnsLocale.code);
  return <DateRangeSelectBlock locale={dateFnsLocale} formatToken={formatToken} {...props} />;
}
