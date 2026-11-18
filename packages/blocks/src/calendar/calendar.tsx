/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Calendar as PropelCalendar } from "@makeplane/propel/components/calendar";
import type { CalendarProps } from "@makeplane/propel/components/calendar";
import { useCalendarLabels } from "./use-calendar-labels";

/** Propel's own English names, used by `Calendar` when it is given none (see `labelNextYear` and friends). */
const PROPEL_ARROW_NAMES = {
  previousYear: "Previous year",
  nextYear: "Next year",
  previousYearPage: "Previous 12 years",
  nextYearPage: "Next 12 years",
};

/**
 * Propel's `Calendar` with its screen reader names in the interface language, and the keyboard behaviour its month
 * and year views lack. Use this instead of importing propel's directly; a caller's own `labels` win over the
 * translated ones.
 *
 * Propel keeps the view (days, months, years) to itself, so the two keys below are done from outside:
 *
 * - **Escape** in the month or year view goes back to the day view instead of closing the popover around the calendar.
 *   Propel has no way to be told "show the days", so the calendar is mounted again on the month that was showing.
 * - **PageUp and PageDown** in the month view go to the previous and next year, and in the year view to the previous
 *   and next 12 years, as they go by month in the day grid. The two arrows are found by their translated names.
 */
export function Calendar({ labels, defaultMonth, onMonthChange, ...props }: CalendarProps) {
  const translatedLabels = useCalendarLabels();
  const allLabels = { ...translatedLabels, ...labels };
  // refs
  const rootRef = useRef<HTMLDivElement>(null);
  const displayedMonth = useRef<Date | undefined>(props.month ?? defaultMonth);
  // states
  const [resetCount, setResetCount] = useState(0);

  // After going back to the day view, focus the first control of the header, where the month and year buttons are
  useEffect(() => {
    if (resetCount > 0) rootRef.current?.querySelector("button")?.focus();
  }, [resetCount]);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return;
    const root = rootRef.current;
    // Only the day view has a grid; the month and year views are a group of buttons
    if (!root || root.querySelector('[role="grid"]')) return;

    if (event.key === "Escape") {
      // Stop it here: the popover around the calendar closes on Escape, and this one only steps back
      event.stopPropagation();
      event.preventDefault();
      setResetCount((count) => count + 1);
      return;
    }

    if (event.key === "PageDown" || event.key === "PageUp") {
      const forward = event.key === "PageDown";
      const names = forward
        ? [
            allLabels.labelNextYear?.() ?? PROPEL_ARROW_NAMES.nextYear,
            allLabels.labelNextYearPage?.() ?? PROPEL_ARROW_NAMES.nextYearPage,
          ]
        : [
            allLabels.labelPreviousYear?.() ?? PROPEL_ARROW_NAMES.previousYear,
            allLabels.labelPreviousYearPage?.() ?? PROPEL_ARROW_NAMES.previousYearPage,
          ];
      // Only the arrow of the view that is showing exists, so at most one of the two names is on the page
      const arrow = Array.from(root.querySelectorAll<HTMLButtonElement>("button")).find((button) =>
        names.includes(button.getAttribute("aria-label") ?? "")
      );
      if (!arrow) return;
      event.preventDefault();
      if (!arrow.disabled) arrow.click();
    }
  };

  return (
    // `contents`: the wrapper only listens for keys and takes no part in the layout
    <div ref={rootRef} className="contents" onKeyDown={handleKeyDown}>
      <PropelCalendar
        // A new key mounts the calendar again, which shows the day view
        key={resetCount}
        {...props}
        defaultMonth={resetCount > 0 ? displayedMonth.current : defaultMonth}
        onMonthChange={(month) => {
          displayedMonth.current = month;
          onMonthChange?.(month);
        }}
        labels={allLabels}
      />
    </div>
  );
}

Calendar.displayName = "blocks.Calendar";
