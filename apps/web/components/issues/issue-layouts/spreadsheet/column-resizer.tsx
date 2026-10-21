/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { KeyboardEvent, PointerEvent } from "react";
import { useRef } from "react";
import { useTranslation } from "@plane/i18n";
import type { TSpreadsheetColumnWidths } from "@/helpers/spreadsheet-column-width";
import { SPREADSHEET_WORK_ITEM_COLUMN_KEY } from "@/helpers/spreadsheet-column-width";
import type { TSpreadsheetColumnWidthControls } from "@/hooks/use-spreadsheet-column-widths";

/** Attribute that marks the header cells whose rendered width is measured when a drag starts. */
export const SPREADSHEET_COLUMN_KEY_ATTRIBUTE = "data-column-key";

const KEYBOARD_STEP = 16;

type Props = TSpreadsheetColumnWidthControls & {
  columnKey: string;
};

/** Rendered widths of the property columns (and of this one), taken from the header row. */
const measureColumns = (cell: HTMLElement, columnKey: string): TSpreadsheetColumnWidths => {
  const measured: TSpreadsheetColumnWidths = {};
  cell.parentElement?.querySelectorAll<HTMLElement>(`[${SPREADSHEET_COLUMN_KEY_ATTRIBUTE}]`).forEach((column) => {
    const key = column.getAttribute(SPREADSHEET_COLUMN_KEY_ATTRIBUTE);
    if (key && (key !== SPREADSHEET_WORK_ITEM_COLUMN_KEY || key === columnKey))
      measured[key] = column.getBoundingClientRect().width;
  });
  return measured;
};

/**
 * Drag handle on the right edge of a spreadsheet header cell. Drag to resize, double-click to reset the column
 * to its default width, or focus it and use the left and right arrow keys.
 */
export function ColumnResizer(props: Props) {
  const { columnKey, previewWidth, commitWidth, resetWidth } = props;
  const { t } = useTranslation();
  const dragRef = useRef<{ startX: number; startWidth: number; measured: TSpreadsheetColumnWidths } | null>(null);
  const frameRef = useRef<number | null>(null);

  const widthAt = (clientX: number) => {
    const drag = dragRef.current;
    return drag ? drag.startWidth + (clientX - drag.startX) : 0;
  };

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      startX: event.clientX,
      startWidth: cell.getBoundingClientRect().width,
      measured: measureColumns(cell, columnKey),
    };
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    const width = widthAt(event.clientX);
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null;
      previewWidth(columnKey, width, drag.measured);
    });
  };

  const handlePointerEnd = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    const width = widthAt(event.clientX);
    dragRef.current = null;
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId))
      event.currentTarget.releasePointerCapture(event.pointerId);
    commitWidth(columnKey, width, drag.measured);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    event.preventDefault();
    event.stopPropagation();
    const step = event.key === "ArrowRight" ? KEYBOARD_STEP : -KEYBOARD_STEP;
    commitWidth(columnKey, cell.getBoundingClientRect().width + step, measureColumns(cell, columnKey));
  };

  return (
    // a separator with a value is focusable and operable, which is what a column resize handle is
    // oxlint-disable-next-line jsx-a11y/no-noninteractive-tabindex, jsx-a11y/no-noninteractive-element-interactions -- ARIA window splitter pattern
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={t("aria_labels.common.resize_column")}
      tabIndex={0}
      className="hover:after:bg-accent-strong focus-visible:after:bg-accent-strong absolute inset-y-0 right-0 z-[1] w-2 cursor-col-resize touch-none outline-none after:absolute after:inset-y-1 after:right-0.5 after:w-px after:bg-transparent"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onKeyDown={handleKeyDown}
      onClick={(event) => event.stopPropagation()}
      onDoubleClick={(event) => {
        event.stopPropagation();
        resetWidth(columnKey);
      }}
    />
  );
}
