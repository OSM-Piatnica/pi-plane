/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { START_OF_THE_WEEK_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Select } from "@plane/blocks/select";
import { cn } from "@plane/utils";
// hooks
import { useCalendarLocale } from "@/hooks/use-calendar-locale";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";

type TDayOption = { value: number };

type TWeekendDaysSelect = {
  value: number[];
  onChange: (days: number[]) => void;
  disabled?: boolean;
  className?: string;
};

// Position of a weekday in a week that starts on the given day
const getDayPosition = (day: number, startOfTheWeek: number) => (day + 7 - startOfTheWeek) % 7;

/** A checkbox per weekday to pick the non-working days; at least one day has to stay a working day. */
export const WeekendDaysSelect = observer(function WeekendDaysSelect(props: TWeekendDaysSelect) {
  const { value, onChange, disabled = false, className } = props;
  // hooks
  const { t } = useTranslation();
  const { getWeekdayName } = useCalendarLocale();
  const startOfTheWeek = useStartOfTheWeek();

  // Every day of the week as the rows of the list, starting on the day the person's week starts
  const dayOptions: TDayOption[] = START_OF_THE_WEEK_OPTIONS.map((day) => ({ value: day.value })).toSorted(
    (a, b) => getDayPosition(a.value, startOfTheWeek) - getDayPosition(b.value, startOfTheWeek)
  );

  // The selected days named in the order they appear in the person's week
  const getTriggerLabel = (days: number[]) => {
    if (days.length === 0) return t("common.none");
    return days
      .toSorted((a, b) => getDayPosition(a, startOfTheWeek) - getDayPosition(b, startOfTheWeek))
      .map((day) => getWeekdayName(day))
      .join(", ");
  };

  return (
    <Select<TDayOption>
      multiple
      valueIds={value.map(String)}
      getValues={() => dayOptions}
      onChange={(ids) => {
        // Nothing could be scheduled if every day were off
        if (ids.length >= dayOptions.length) return;
        onChange(ids.map(Number).toSorted((a, b) => a - b));
      }}
      getOptionValue={(option) => String(option.value)}
      getOptionLabel={(option) => getWeekdayName(option.value)}
      showSearch={false}
      pinSelected={false}
      contentSizing="anchor"
      disabled={disabled}
    >
      <Select.Trigger<TDayOption> variant="select-md" className={cn("w-full", className)}>
        <span className="min-w-0 grow truncate text-left">{getTriggerLabel(value)}</span>
      </Select.Trigger>
    </Select>
  );
});
