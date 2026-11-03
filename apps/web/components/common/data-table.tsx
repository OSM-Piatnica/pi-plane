/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { Fragment, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@makeplane/propel/components/table";
import type { TableRowProps, TableVariant } from "@makeplane/propel/components/table";
import { TableHead as TableHeadElement } from "@makeplane/propel/elements/table";
import { Loader } from "@plane/blocks/skeleton";
import { getDraggedWidth, getKeyResizedWidth, withoutColumnWidth } from "@/helpers/column-resize";
import { getValueFromLocalStorage, setValueIntoLocalStorage } from "@/hooks/use-local-storage";

export type DataTableColumn<T> = {
  key: string;
  /** Column title. The header label unless `thRender` supplies richer content. */
  content: string;
  /**
   * Custom header content (a sort menu, a right-aligned numeric title). Rendered through the
   * elements-tier `TableHead`, which takes children; the ready-made one takes a string label only.
   */
  thRender?: () => ReactNode;
  tdRender: (rowData: T) => ReactNode;
  /**
   * Cell padding mode. `cell` (default) is propel's `px-3 py-2` text cell. `trigger` drops the
   * cell's own padding so a full-height control can own the box — without it, a control offset
   * into the cell's gutter is clipped by the content region's `truncate`.
   */
  padding?: "cell" | "trigger";
  /** Starting width in px of a resizable table's column. @default 160 */
  defaultWidth?: number;
  /** Narrowest width in px a person can drag a resizable table's column to. @default 80 */
  minWidth?: number;
};

const DEFAULT_COLUMN_WIDTH = 160;
const DEFAULT_MIN_COLUMN_WIDTH = 80;

/** Row attributes: the `<tr>` props propel forwards, plus `data-*` flags a wrapping selector can style. */
export type DataTableRowProps = Omit<TableRowProps, "children" | "render"> &
  Record<`data-${string}`, string | undefined>;

export type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  data: T[];
  keyExtractor: (rowData: T) => string;
  /**
   * Wraps a row. Receives the rendered cells and must return them inside a `TableRow` (the caller
   * owns the row when it needs a `render`, an id, or event handlers on it).
   */
  renderRow?: (props: { rowData: T; children: ReactNode }) => ReactNode;
  /** Attributes for a row, e.g. a `data-*` flag a wrapping selector can style (dimmed rows). */
  getRowProps?: (rowData: T) => DataTableRowProps;
  /** Replaces the body with three skeleton rows. */
  isLoading?: boolean;
  /** `table` draws row dividers only; `spreadsheet` draws the full grid. @default "table" */
  variant?: TableVariant;
  /**
   * Lets people drag the right edge of a column header (or use the arrow keys on it) to resize that column.
   * The widths are kept in local storage under this key. Without it the columns size themselves, as before.
   */
  resizeStorageKey?: string;
};

type ColumnResizeHandleProps = {
  label: string;
  width: number;
  minWidth: number;
  onResize: (width: number) => void;
  onCommit: (width: number) => void;
  onReset: () => void;
};

/** The draggable right edge of a resizable column's header; a keyboard-focusable separator. */
function ColumnResizeHandle(props: ColumnResizeHandleProps) {
  const { label, width, minWidth, onResize, onCommit, onReset } = props;
  // where the drag started, and the width the column had then
  const dragRef = useRef<{ startX: number; startWidth: number; width: number } | null>(null);

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { startX: event.clientX, startWidth: width, width };
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    drag.width = getDraggedWidth(drag.startWidth, drag.startX, event.clientX, minWidth);
    onResize(drag.width);
  };

  const handlePointerUp = () => {
    const drag = dragRef.current;
    dragRef.current = null;
    if (drag) onCommit(drag.width);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const next = getKeyResizedWidth(width, event.key, minWidth);
    if (next === null) return;
    event.preventDefault();
    onResize(next);
    onCommit(next);
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={width}
      aria-valuemin={minWidth}
      tabIndex={0}
      className="hover:bg-accent-strong/40 focus-visible:bg-accent-strong/60 absolute top-0 -right-1 z-10 h-full w-2 cursor-col-resize touch-none select-none focus-visible:outline-none"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      onKeyDown={handleKeyDown}
      onDoubleClick={onReset}
    />
  );
}

/**
 * The `columns` / `data` / `keyExtractor` table of the legacy `@plane/blocks/tables` `Table`, rendered with
 * propel's table parts. Chrome (dividers, header fill, cell padding, the rounded scroll frame) is
 * propel's; there is no className axis. Headers are `TableHead label` unless a column brings its
 * own `thRender`, and every cell is `TableCell padding="cell"` unless the column opts into
 * `padding: "trigger"`.
 */
export function DataTable<T>(props: DataTableProps<T>) {
  const {
    columns,
    data,
    keyExtractor,
    renderRow,
    getRowProps,
    isLoading = false,
    variant = "table",
    resizeStorageKey,
  } = props;
  // the widths people dragged their columns to; a column they never touched keeps its default
  const [widths, setWidths] = useState<Record<string, number>>(() =>
    resizeStorageKey ? getValueFromLocalStorage(resizeStorageKey, {}) : {}
  );
  const isResizable = resizeStorageKey !== undefined;
  const getWidth = (column: DataTableColumn<T>) => widths[column.key] ?? column.defaultWidth ?? DEFAULT_COLUMN_WIDTH;
  const getMinWidth = (column: DataTableColumn<T>) => column.minWidth ?? DEFAULT_MIN_COLUMN_WIDTH;
  const saveWidths = (next: Record<string, number>) => {
    if (resizeStorageKey) setValueIntoLocalStorage(resizeStorageKey, next);
  };
  const renderHeaderContent = (column: DataTableColumn<T>) => {
    if (!isResizable) return column.thRender?.();
    const width = getWidth(column);
    return (
      <div className="relative" style={{ width }}>
        {column.thRender ? column.thRender() : <span className="block truncate">{column.content}</span>}
        <ColumnResizeHandle
          label={column.content}
          width={width}
          minWidth={getMinWidth(column)}
          onResize={(next) => setWidths((current) => ({ ...current, [column.key]: next }))}
          onCommit={(next) => saveWidths({ ...widths, [column.key]: next })}
          onReset={() => {
            const rest = withoutColumnWidth(widths, column.key);
            setWidths(rest);
            saveWidths(rest);
          }}
        />
      </div>
    );
  };

  return (
    <Table variant={variant}>
      <TableHeader>
        <TableRow>
          {columns.map((column) =>
            column.thRender || isResizable ? (
              <TableHeadElement key={column.key} variant={variant} pinned="none">
                {renderHeaderContent(column)}
              </TableHeadElement>
            ) : (
              <TableHead key={column.key} label={column.content} pinned="none" />
            )
          )}
        </TableRow>
      </TableHeader>
      <TableBody>
        {isLoading ? (
          <TableRow>
            <TableCell pinned="none" padding="cell" colSpan={columns.length}>
              <Loader className="flex flex-col gap-2 py-2">
                <Loader.Item height="28px" width="100%" />
                <Loader.Item height="28px" width="100%" />
                <Loader.Item height="28px" width="100%" />
              </Loader>
            </TableCell>
          </TableRow>
        ) : (
          data.map((rowData) => {
            const key = keyExtractor(rowData);
            const cells = columns.map((column) => (
              <TableCell key={`${column.key}-${key}`} pinned="none" padding={column.padding ?? "cell"}>
                {isResizable ? (
                  <div className="min-w-0" style={{ width: getWidth(column) }}>
                    {column.tdRender(rowData)}
                  </div>
                ) : (
                  column.tdRender(rowData)
                )}
              </TableCell>
            ));
            if (renderRow) return <Fragment key={key}>{renderRow({ rowData, children: cells })}</Fragment>;
            return (
              <TableRow key={key} {...getRowProps?.(rowData)}>
                {cells}
              </TableRow>
            );
          })
        )}
      </TableBody>
    </Table>
  );
}
