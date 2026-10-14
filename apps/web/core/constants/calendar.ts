/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TCalendarLayouts } from "@plane/types";
import { EStartOfTheWeek } from "@plane/types";

// month numbers (1-12), names are localized via `useCalendarLocale`
export const MONTHS_LIST: number[] = Array.from({ length: 12 }, (_, index) => index + 1);

// days of the week, names are localized via `useCalendarLocale`
export const DAYS_LIST: { value: EStartOfTheWeek }[] = [
  { value: EStartOfTheWeek.SUNDAY },
  { value: EStartOfTheWeek.MONDAY },
  { value: EStartOfTheWeek.TUESDAY },
  { value: EStartOfTheWeek.WEDNESDAY },
  { value: EStartOfTheWeek.THURSDAY },
  { value: EStartOfTheWeek.FRIDAY },
  { value: EStartOfTheWeek.SATURDAY },
];

export const CALENDAR_LAYOUTS: {
  [layout in TCalendarLayouts]: {
    key: TCalendarLayouts;
    i18n_title: string;
  };
} = {
  month: {
    key: "month",
    i18n_title: "calendar_ui.month_layout",
  },
  week: {
    key: "week",
    i18n_title: "calendar_ui.week_layout",
  },
};
