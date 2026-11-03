/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// a keyboard step of a column's resize handle, in px
export const RESIZE_KEY_STEP = 16;

/** The width of a column that was dragged from `startX` to `currentX`, never narrower than `minWidth`. */
export const getDraggedWidth = (startWidth: number, startX: number, currentX: number, minWidth: number) =>
  Math.max(minWidth, Math.round(startWidth + currentX - startX));

/** The width after an arrow key on the resize handle (right widens, left narrows); null for any other key. */
export const getKeyResizedWidth = (width: number, key: string, minWidth: number) => {
  if (key !== "ArrowLeft" && key !== "ArrowRight") return null;
  return Math.max(minWidth, width + (key === "ArrowRight" ? RESIZE_KEY_STEP : -RESIZE_KEY_STEP));
};

/** The widths without the one of `key`, so that column goes back to its default. */
export const withoutColumnWidth = (widths: Record<string, number>, key: string) =>
  Object.fromEntries(Object.entries(widths).filter(([column]) => column !== key));
