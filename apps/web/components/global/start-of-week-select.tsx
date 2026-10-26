/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { START_OF_THE_WEEK_OPTIONS } from "@plane/constants";
import { Select } from "@plane/blocks/select";
import type { EStartOfTheWeek } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { useCalendarLocale } from "@/hooks/use-calendar-locale";

type TStartOfWeekOption = (typeof START_OF_THE_WEEK_OPTIONS)[number];

type TStartOfWeekSelect = {
  value: EStartOfTheWeek | undefined;
  onChange: (value: EStartOfTheWeek) => void;
  disabled?: boolean;
  className?: string;
};

/** The seven days, named in the person's language, to pick the first day of the week from. */
export const StartOfWeekSelect = observer(function StartOfWeekSelect(props: TStartOfWeekSelect) {
  const { value, onChange, disabled = false, className } = props;
  // hooks
  const { getWeekdayName } = useCalendarLocale();
  // derived values
  const selectedOption = START_OF_THE_WEEK_OPTIONS.find((option) => option.value === value) ?? null;

  return (
    <Select<TStartOfWeekOption>
      getValues={() => START_OF_THE_WEEK_OPTIONS}
      value={selectedOption}
      onChange={(next) => onChange(Number(next) as EStartOfTheWeek)}
      getOptionValue={(option) => String(option.value)}
      getOptionLabel={(option) => getWeekdayName(option.value)}
      showSearch={false}
      pinSelected={false}
      contentSizing="anchor"
      disabled={disabled}
    >
      <Select.Trigger<TStartOfWeekOption> variant="select-md" className={cn("w-full", className)}>
        {(options) => (
          <span className="min-w-0 grow truncate text-left">
            {options[0] ? getWeekdayName(options[0].value) : null}
          </span>
        )}
      </Select.Trigger>
    </Select>
  );
});
