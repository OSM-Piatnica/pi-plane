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

// Every day of the week, Sunday first, as the rows of the list
const DAY_OPTIONS: TDayOption[] = START_OF_THE_WEEK_OPTIONS.map(({ value }) => ({ value }));

/** A checkbox per weekday to pick the non-working days; at least one day has to stay a working day. */
export const WeekendDaysSelect = observer(function WeekendDaysSelect(props: TWeekendDaysSelect) {
  const { value, onChange, disabled = false, className } = props;
  // hooks
  const { t } = useTranslation();
  const { getWeekdayName } = useCalendarLocale();
  const startOfTheWeek = useStartOfTheWeek();

  // The selected days named in the order they appear in the person's week
  const getTriggerLabel = (days: number[]) => {
    if (days.length === 0) return t("common.none");
    return days
      .toSorted((a, b) => ((a + 7 - startOfTheWeek) % 7) - ((b + 7 - startOfTheWeek) % 7))
      .map((day) => getWeekdayName(day))
      .join(", ");
  };

  return (
    <Select<TDayOption>
      multiple
      valueIds={value.map(String)}
      getValues={() => DAY_OPTIONS}
      onChange={(ids) => {
        // Nothing could be scheduled if every day were off
        if (ids.length >= DAY_OPTIONS.length) return;
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
