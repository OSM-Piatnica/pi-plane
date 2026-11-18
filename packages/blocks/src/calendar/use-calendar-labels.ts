/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import { format } from "date-fns";
import type { Locale } from "date-fns";
import type { CalendarLabels } from "@makeplane/propel/components/calendar";
import { useTranslation } from "@plane/i18n";

/** The slice of react-day-picker's `DateLib` the day labels need; it formats in the calendar's own locale. */
type DayLabelDateLib = { format: (date: Date, formatStr: string) => string };
type DayLabelOptions = { locale?: Locale };

/**
 * The names a screen reader reads for the calendar's controls and days, in the interface language.
 *
 * react-day-picker and propel's `Calendar` ship English defaults ("Choose the Month", "Go to the Previous Month",
 * "Today, ..."); the dates inside them already follow the calendar's `locale`, so a Polish reader heard
 * "Choose the Month, listopada". These replace every default string a person can reach.
 */
export function useCalendarLabels(): CalendarLabels {
  const { t, currentLocale } = useTranslation();

  // `currentLocale` is a dependency on purpose: `t` keeps its identity when the language changes.
  return useMemo(() => {
    // Asks `t` for the string with each placeholder left as its own `{name}` text, then fills it in here. ICU inserts a
    // value as it is, so this reads the same in the app, and it does not depend on ICU running: it does not in jsdom,
    // where every `{date}` of every string stays literal and the day names would be wrong in the tests.
    const fill = (key: string, values: Record<string, string>) =>
      Object.entries(values).reduce(
        (text, [name, value]) => text.replaceAll(`{${name}}`, value),
        t(key, Object.fromEntries(Object.keys(values).map((name) => [name, `{${name}}`])))
      );
    const formatDay = (date: Date, options?: DayLabelOptions, dateLib?: DayLabelDateLib) =>
      dateLib ? dateLib.format(date, "PPPP") : format(date, "PPPP", { locale: options?.locale });

    return {
      labelMonthDropdown: () => t("aria_labels.calendar.choose_month"),
      labelYearDropdown: () => t("aria_labels.calendar.choose_year"),
      labelPrevious: () => t("aria_labels.calendar.previous_month"),
      labelNext: () => t("aria_labels.calendar.next_month"),
      labelGridcell: (date, modifiers, options, dateLib) => {
        const label = formatDay(date, options, dateLib);
        return modifiers?.today ? fill("aria_labels.calendar.today_date", { date: label }) : label;
      },
      labelDayButton: (date, modifiers, options, dateLib) => {
        let label = formatDay(date, options, dateLib);
        if (modifiers.today) label = fill("aria_labels.calendar.today_date", { date: label });
        if (modifiers.selected) label = fill("aria_labels.calendar.selected_date", { date: label });
        return label;
      },
      labelPreviousYear: () => t("aria_labels.calendar.previous_year"),
      labelNextYear: () => t("aria_labels.calendar.next_year"),
      labelPreviousYearPage: () => t("aria_labels.calendar.previous_year_page"),
      labelNextYearPage: () => t("aria_labels.calendar.next_year_page"),
      labelMonthView: (year) => fill("aria_labels.calendar.month_view", { year }),
      labelYearView: (firstYear, lastYear) =>
        fill("aria_labels.calendar.year_view", { first_year: firstYear, last_year: lastYear }),
    };
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- see the comment above
  }, [t, currentLocale]);
}
