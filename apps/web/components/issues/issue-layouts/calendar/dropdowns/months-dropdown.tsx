/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Popover, PopoverContent, PopoverTrigger } from "@makeplane/propel/components/popover";
import { useTranslation } from "@plane/i18n";
import { ChevronLeftOutline, ChevronRightOutline } from "@makeplane/propel/icons";
//hooks
// icons
// constants
import { getDate } from "@plane/utils";
import { MONTHS_LIST } from "@plane/constants";
import { useCalendarView } from "@/hooks/store/use-calendar-view";
import { useCalendarLocale } from "@/hooks/use-calendar-locale";
import type { ICycleIssuesFilter } from "@/store/issue/cycle";
import type { IModuleIssuesFilter } from "@/store/issue/module";
import type { IProjectIssuesFilter } from "@/store/issue/project";
import type { IProjectViewIssuesFilter } from "@/store/issue/project-views";
// helpers

interface Props {
  issuesFilterStore: IProjectIssuesFilter | IModuleIssuesFilter | ICycleIssuesFilter | IProjectViewIssuesFilter;
}
export const CalendarMonthsDropdown = observer(function CalendarMonthsDropdown(props: Props) {
  const { issuesFilterStore } = props;

  const { t } = useTranslation();
  const { getMonthName } = useCalendarLocale();
  const issueCalendarView = useCalendarView();

  const calendarLayout = issuesFilterStore.issueFilters?.displayFilters?.calendar?.layout ?? "month";

  const { activeMonthDate } = issueCalendarView.calendarFilters;

  const getWeekLayoutHeader = (): string => {
    const allDaysOfActiveWeek = issueCalendarView.allDaysOfActiveWeek;

    if (!allDaysOfActiveWeek) return t("calendar_ui.week_view");

    const daysList = Object.keys(allDaysOfActiveWeek);

    const firstDay = getDate(daysList[0]);
    const lastDay = getDate(daysList[daysList.length - 1]);

    if (!firstDay || !lastDay) return t("calendar_ui.week_view");

    if (firstDay.getMonth() === lastDay.getMonth() && firstDay.getFullYear() === lastDay.getFullYear())
      return `${getMonthName(firstDay.getMonth() + 1)} ${firstDay.getFullYear()}`;

    if (firstDay.getFullYear() !== lastDay.getFullYear()) {
      return `${getMonthName(firstDay.getMonth() + 1, "short")} ${firstDay.getFullYear()} - ${getMonthName(
        lastDay.getMonth() + 1,
        "short"
      )} ${lastDay.getFullYear()}`;
    } else
      return `${getMonthName(firstDay.getMonth() + 1, "short")} - ${getMonthName(
        lastDay.getMonth() + 1,
        "short"
      )} ${lastDay.getFullYear()}`;
  };

  const handleDateChange = (date: Date) => {
    issueCalendarView.updateCalendarFilters({
      activeMonthDate: date,
    });
  };

  return (
    <Popover>
      <PopoverTrigger
        disabled={calendarLayout === "week"}
        render={
          <button type="button" className="text-18 font-semibold outline-none">
            {calendarLayout === "month"
              ? `${getMonthName(activeMonthDate.getMonth() + 1)} ${activeMonthDate.getFullYear()}`
              : getWeekLayoutHeader()}
          </button>
        }
      />
      <PopoverContent variant="rich" side="bottom" align="start" collisionPadding={12}>
        <div className="w-56 divide-y divide-subtle-1">
          <div className="flex items-center justify-between gap-2 pb-3">
            <button
              type="button"
              className="grid place-items-center"
              onClick={() => {
                const previousYear = new Date(activeMonthDate.getFullYear() - 1, activeMonthDate.getMonth(), 1);
                handleDateChange(previousYear);
              }}
            >
              <ChevronLeftOutline height={14} width={14} />
            </button>
            <span className="text-11">{activeMonthDate.getFullYear()}</span>
            <button
              type="button"
              className="grid place-items-center"
              onClick={() => {
                const nextYear = new Date(activeMonthDate.getFullYear() + 1, activeMonthDate.getMonth(), 1);
                handleDateChange(nextYear);
              }}
            >
              <ChevronRightOutline height={14} width={14} />
            </button>
          </div>
          <div className="grid grid-cols-4 items-stretch justify-items-stretch gap-4 pt-3">
            {MONTHS_LIST.map((monthNumber, index) => (
              <button
                key={monthNumber}
                type="button"
                className="rounded-sm py-0.5 text-11 hover:bg-layer-1"
                onClick={() => {
                  const newDate = new Date(activeMonthDate.getFullYear(), index, 1);
                  handleDateChange(newDate);
                }}
              >
                {getMonthName(monthNumber, "short")}
              </button>
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
});
