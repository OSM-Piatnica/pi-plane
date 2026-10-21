/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Key of the first, sticky column (identifier and title); the property columns use their property key. */
export const SPREADSHEET_WORK_ITEM_COLUMN_KEY = "work_item";

/** The width of a property column that has not been resized: 9rem, the old `min-w-36`. */
export const SPREADSHEET_COLUMN_DEFAULT_WIDTH = 144;
/** The least width of the work item column: 15rem, the old `min-w-60`. */
export const SPREADSHEET_WORK_ITEM_COLUMN_MIN_WIDTH = 240;

const PROPERTY_COLUMN_LIMITS = { min: 96, max: 640 };
// the cells of the work item column have `max-w-lg` (32rem)
const WORK_ITEM_COLUMN_LIMITS = { min: SPREADSHEET_WORK_ITEM_COLUMN_MIN_WIDTH, max: 512 };

export type TSpreadsheetColumnWidths = Record<string, number>;

/** Keeps a column width inside the range its column allows. */
export const clampSpreadsheetColumnWidth = (columnKey: string, width: number): number => {
  const { min, max } =
    columnKey === SPREADSHEET_WORK_ITEM_COLUMN_KEY ? WORK_ITEM_COLUMN_LIMITS : PROPERTY_COLUMN_LIMITS;
  return Math.round(Math.min(max, Math.max(min, width)));
};

/** Reads saved column widths defensively: anything that is not a positive number is dropped, the rest is clamped. */
export const sanitizeSpreadsheetColumnWidths = (raw: unknown): TSpreadsheetColumnWidths => {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const widths: TSpreadsheetColumnWidths = {};
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === "number" && Number.isFinite(value) && value > 0)
      widths[key] = clampSpreadsheetColumnWidth(key, value);
  }
  return widths;
};

/**
 * The widths to apply while a column is dragged to `width`. `measured` holds the rendered width of every
 * column when the drag began, so the first resize freezes the other columns where they are instead of
 * making them jump. The work item column is left to take the remaining space until it is resized itself.
 */
export const buildSpreadsheetColumnWidths = (
  columnKey: string,
  width: number,
  measured: TSpreadsheetColumnWidths,
  saved: TSpreadsheetColumnWidths
): TSpreadsheetColumnWidths => {
  const next = sanitizeSpreadsheetColumnWidths(measured);
  delete next[SPREADSHEET_WORK_ITEM_COLUMN_KEY];
  const savedWorkItemWidth = saved[SPREADSHEET_WORK_ITEM_COLUMN_KEY];
  if (savedWorkItemWidth !== undefined) next[SPREADSHEET_WORK_ITEM_COLUMN_KEY] = savedWorkItemWidth;
  next[columnKey] = clampSpreadsheetColumnWidth(columnKey, width);
  return next;
};
