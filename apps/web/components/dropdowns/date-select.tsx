/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { DateRangeSelect as DateRangeSelectBlock, DateSelect as DateSelectBlock } from "@plane/blocks/property-select";
import type { DateRangeSelectProps, DateSelectProps } from "@plane/blocks/property-select";
// hooks
import { useCalendarLocale } from "@/hooks/use-calendar-locale";

/**
 * Web bindings for the presentational date pickers: they fill in the `date-fns` locale of the
 * user's language, so the calendar and the month names in the trigger label are not English-only.
 * A caller can still pass its own `locale`.
 */
export function DateSelect(props: DateSelectProps) {
  const { dateFnsLocale } = useCalendarLocale();
  return <DateSelectBlock locale={dateFnsLocale} {...props} />;
}

export function DateRangeSelect(props: DateRangeSelectProps) {
  const { dateFnsLocale } = useCalendarLocale();
  return <DateRangeSelectBlock locale={dateFnsLocale} {...props} />;
}
