/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, observable } from "mobx";

/**
 * The calendar offers two independent layers:
 * - `scheduled`: planned work, placed from `start_date` to `finish_date` (or a single marker when only one end exists)
 * - `deadlines`: items placed on their due date (`target_date`)
 * A start-due bar is never drawn: due is a deadline, not part of the work duration.
 */
export type TCalendarLayer = "scheduled" | "deadlines";

export const CALENDAR_LAYERS: TCalendarLayer[] = ["scheduled", "deadlines"];
export const DEFAULT_CALENDAR_LAYER: TCalendarLayer = "scheduled";

const STORAGE_KEY = "plane-calendar-layer";

const readStoredLayer = (): TCalendarLayer => {
  try {
    const stored = typeof window === "undefined" ? null : window.localStorage.getItem(STORAGE_KEY);
    if (stored === "scheduled" || stored === "deadlines") return stored;
  } catch {
    // storage may be unavailable
  }
  return DEFAULT_CALENDAR_LAYER;
};

/** Shared (store + components) observable holding the active calendar layer. */
export const calendarLayerState = observable({ layer: readStoredLayer() as TCalendarLayer });

export const setCalendarLayer = action((layer: TCalendarLayer) => {
  calendarLayerState.layer = layer;
  try {
    window.localStorage.setItem(STORAGE_KEY, layer);
  } catch {
    // storage may be unavailable
  }
});

/** Server group-by / date field that backs each layer. */
export const CALENDAR_LAYER_DATE_FIELD = {
  scheduled: "finish_date",
  deadlines: "target_date",
} as const;

type TCalendarDates = {
  start_date?: string | null;
  finish_date?: string | null;
  target_date?: string | null;
};

const day = (value: string | null | undefined): string | null => (value ? value.slice(0, 10) : null);

const parseDay = (value: string): Date => {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};

const formatDay = (date: Date): string => date.toISOString().slice(0, 10);

/** Adds whole calendar days to a `yyyy-mm-dd` string without any local time zone involvement. */
export const addDaysToDate = (value: string, days: number): string => {
  const date = parseDay(value.slice(0, 10));
  date.setUTCDate(date.getUTCDate() + days);
  return formatDay(date);
};

export const diffInDays = (from: string, to: string): number =>
  Math.round((parseDay(to.slice(0, 10)).getTime() - parseDay(from.slice(0, 10)).getTime()) / 86_400_000);

/**
 * @description The span an item occupies in the Scheduled layer. A single-ended item (only start or only
 * finish) is a one-day marker. Returns null when the item has no schedule dates at all. If a malformed
 * span ends before it starts, it is shown as a marker on the finish day.
 */
export const getScheduledSpan = (dates: TCalendarDates): { start: string; end: string } | null => {
  const start = day(dates.start_date);
  const finish = day(dates.finish_date);
  if (start && finish) return finish < start ? { start: finish, end: finish } : { start, end: finish };
  const single = start ?? finish;
  return single ? { start: single, end: single } : null;
};

/**
 * @description Builds `date -> item ids` for the visible range in the given layer.
 * Scheduled items appear on every day of their span; deadline items only on their due date.
 */
export const buildCalendarPlacement = (
  layer: TCalendarLayer,
  items: Iterable<{ id: string } & TCalendarDates>,
  rangeStart: string,
  rangeEnd: string
): Record<string, string[]> => {
  const placement: Record<string, string[]> = {};
  const push = (date: string, id: string) => {
    if (date < rangeStart || date > rangeEnd) return;
    (placement[date] ??= []).push(id);
  };
  const seen = new Set<string>();
  for (const item of items) {
    if (!item || seen.has(item.id)) continue;
    seen.add(item.id);
    if (layer === "deadlines") {
      const due = day(item.target_date);
      if (due) push(due, item.id);
      continue;
    }
    const span = getScheduledSpan(item);
    if (!span) continue;
    const from = span.start < rangeStart ? rangeStart : span.start;
    const to = span.end > rangeEnd ? rangeEnd : span.end;
    for (let d = from; d <= to; d = addDaysToDate(d, 1)) push(d, item.id);
  }
  return placement;
};

/**
 * @description Patch for dropping an item from `sourceDate` onto `destinationDate`.
 * - Scheduled: start and finish move by the same number of days (duration preserved); due is never touched.
 * - Deadlines: only the due date changes (it moves to the destination day).
 * Returns null when nothing changes.
 */
export const getCalendarDragPatch = (
  layer: TCalendarLayer,
  dates: TCalendarDates,
  sourceDate: string,
  destinationDate: string
): { start_date?: string; finish_date?: string; target_date?: string } | null => {
  if (sourceDate === destinationDate) return null;
  if (layer === "deadlines") return { target_date: destinationDate };
  const delta = diffInDays(sourceDate, destinationDate);
  if (delta === 0) return null;
  const patch: { start_date?: string; finish_date?: string } = {};
  const start = day(dates.start_date);
  const finish = day(dates.finish_date);
  if (start) patch.start_date = addDaysToDate(start, delta);
  if (finish) patch.finish_date = addDaysToDate(finish, delta);
  return start || finish ? patch : null;
};
