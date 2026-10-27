/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// More than this many days of shading is not worth drawing; the chart never loads a range anywhere near it
const MAX_DAYS = 2000;

/**
 * The left offset, in pixels from the start of the chart, of every day between the two dates that falls on one of
 * `weekendDays` (0 = Sunday ... 6 = Saturday), for a chart that draws each day `dayWidth` pixels wide.
 */
export const getOffDayPositions = (
  chartStart: Date,
  chartEnd: Date,
  dayWidth: number,
  weekendDays: number[]
): number[] => {
  const off = new Set(weekendDays);
  const positions: number[] = [];
  const first = new Date(chartStart.getFullYear(), chartStart.getMonth(), chartStart.getDate());
  const last = new Date(chartEnd.getFullYear(), chartEnd.getMonth(), chartEnd.getDate());
  // Whole days between the two, counted on the calendar so a daylight-saving change does not shift the result
  const dayCount = Math.min(
    Math.round(
      (Date.UTC(last.getFullYear(), last.getMonth(), last.getDate()) -
        Date.UTC(first.getFullYear(), first.getMonth(), first.getDate())) /
        86400000
    ) + 1,
    MAX_DAYS
  );

  for (let index = 0; index < dayCount; index++) {
    const day = new Date(first.getFullYear(), first.getMonth(), first.getDate() + index);
    if (off.has(day.getDay())) positions.push(index * dayWidth);
  }
  return positions;
};
