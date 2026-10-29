/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { getOrderedDays } from "@plane/utils";
import { DAYS_LIST } from "@plane/constants";
// helpers
// hooks
import { isWeekendDay } from "@/helpers/weekend-days";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { useWeekendDays } from "@/hooks/use-weekend-days";
import { useCalendarLocale } from "@/hooks/use-calendar-locale";

type Props = {
  isLoading: boolean;
  showWeekends: boolean;
};

export const CalendarWeekHeader = observer(function CalendarWeekHeader(props: Props) {
  const { isLoading, showWeekends } = props;
  // hooks
  const { getWeekdayName } = useCalendarLocale();
  const startOfWeek = useStartOfTheWeek();
  const weekendDays = useWeekendDays();

  // derived
  const orderedDays = getOrderedDays(DAYS_LIST, (item) => item.value, startOfWeek);
  const visibleDays = showWeekends ? orderedDays : orderedDays.filter((day) => !isWeekendDay(day.value, weekendDays));

  return (
    <div
      className="relative sticky top-0 z-[1] grid divide-subtle-1 text-13 font-medium md:divide-x-[0.5px]"
      style={{ gridTemplateColumns: `repeat(${visibleDays.length}, minmax(0, 1fr))` }}
    >
      {isLoading && (
        <div className="absolute h-[1.5px] w-3/4 animate-[bar-loader_2s_linear_infinite] bg-accent-primary" />
      )}
      {visibleDays.map((day) => {
        return (
          <div key={day.value} className="flex h-11 items-center justify-center bg-layer-1 px-4 md:justify-end">
            {getWeekdayName(day.value, "short")}
          </div>
        );
      })}
    </div>
  );
});
