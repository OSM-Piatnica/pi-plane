/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { renderHook } from "@testing-library/react";
import { pl } from "date-fns/locale";
import { describe, expect, it, vi } from "vitest";
import { useCalendarLabels } from "./use-calendar-labels";

// A `t` that shows the key and the placeholders it was given, so what the hook asks for can be asserted.
// (hoisted, as vi.mock is, and stable between renders like the real one)
const { t } = vi.hoisted(() => ({
  t: (key: string, params?: Record<string, string>) =>
    params
      ? `${key}(${Object.entries(params)
          .map(([name, value]) => `${name}=${value}`)
          .join(",")})`
      : key,
}));
vi.mock("@plane/i18n", () => ({ useTranslation: () => ({ t, currentLocale: "en" }) }));

const JUNE_15 = new Date(2025, 5, 15);
const none = { today: false, selected: false } as never;
const modifiers = (flags: { today?: boolean; selected?: boolean }) => flags as never;
const labels = () => renderHook(() => useCalendarLabels()).result.current;

describe("useCalendarLabels", () => {
  it("asks for the translation of every control a person can reach", () => {
    const l = labels();

    expect(l.labelMonthDropdown?.({} as never)).toBe("aria_labels.calendar.choose_month");
    expect(l.labelYearDropdown?.({} as never)).toBe("aria_labels.calendar.choose_year");
    expect(l.labelPrevious?.(undefined)).toBe("aria_labels.calendar.previous_month");
    expect(l.labelNext?.(undefined)).toBe("aria_labels.calendar.next_month");
    expect(l.labelPreviousYear?.()).toBe("aria_labels.calendar.previous_year");
    expect(l.labelNextYear?.()).toBe("aria_labels.calendar.next_year");
    expect(l.labelPreviousYearPage?.()).toBe("aria_labels.calendar.previous_year_page");
    expect(l.labelNextYearPage?.()).toBe("aria_labels.calendar.next_year_page");
  });

  it("hands the year and the page bounds to the month and year views", () => {
    const l = labels();

    expect(l.labelMonthView?.("2025")).toBe("aria_labels.calendar.month_view(year=2025)");
    expect(l.labelYearView?.("2020", "2031")).toBe("aria_labels.calendar.year_view(first_year=2020,last_year=2031)");
  });

  it("leaves an ordinary day as its long date in the calendar's locale", () => {
    const l = labels();

    expect(l.labelDayButton?.(JUNE_15, none, { locale: pl })).toBe("niedziela, 15 czerwca 2025");
    expect(l.labelGridcell?.(JUNE_15, none, { locale: pl })).toBe("niedziela, 15 czerwca 2025");
  });

  it("marks today and the selected day with translated words around the date", () => {
    const l = labels();
    const date = "Sunday, June 15th, 2025";

    expect(l.labelDayButton?.(JUNE_15, modifiers({ today: true }))).toBe(
      `aria_labels.calendar.today_date(date=${date})`
    );
    expect(l.labelDayButton?.(JUNE_15, modifiers({ selected: true }))).toBe(
      `aria_labels.calendar.selected_date(date=${date})`
    );
    // Today and selected: the selected suffix goes around the "today" phrase, as react-day-picker orders them.
    expect(l.labelDayButton?.(JUNE_15, modifiers({ today: true, selected: true }))).toBe(
      `aria_labels.calendar.selected_date(date=aria_labels.calendar.today_date(date=${date}))`
    );
    expect(l.labelGridcell?.(JUNE_15, modifiers({ today: true }))).toBe(
      `aria_labels.calendar.today_date(date=${date})`
    );
  });

  it("keeps a stable object while the language does not change", () => {
    const { result, rerender } = renderHook(() => useCalendarLabels());
    const first = result.current;

    rerender();

    expect(result.current).toBe(first);
  });
});
