/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
// plane imports
import { calculateTimeAgo, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// local imports
import { useCalendarLocale } from "./use-calendar-locale";

// English keeps the app's usual "Jan 05, 2024"; other languages use date-fns' localized medium date
// ("5 sty 2024"), which also puts the day, month and year in that language's order.
const ENGLISH_LOCALE_CODE = "en-US";
const ENGLISH_DATE_TOKEN = "MMM dd, yyyy";
const LOCALIZED_DATE_TOKEN = "PP";

/**
 * Date and time text in the user's language, for places that show a fixed date style (the activity
 * feeds): a calendar date, a clock time and a relative "3 days ago".
 */
export const useLocalizedDates = () => {
  const { dateFnsLocale } = useCalendarLocale();

  return useMemo(() => {
    const dateToken = dateFnsLocale.code === ENGLISH_LOCALE_CODE ? ENGLISH_DATE_TOKEN : LOCALIZED_DATE_TOKEN;
    return {
      formatDate: (date: string | Date | undefined | null) => renderFormattedDate(date, dateToken, dateFnsLocale),
      formatTime: (date: string | Date, timeFormat?: "12-hour" | "24-hour") =>
        renderFormattedTime(date, timeFormat, dateFnsLocale),
      timeAgo: (time: string | number | Date | null) => calculateTimeAgo(time, dateFnsLocale),
    };
  }, [dateFnsLocale]);
};
