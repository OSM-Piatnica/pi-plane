/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo, useState } from "react";
import type { TSpreadsheetColumnWidths } from "@/helpers/spreadsheet-column-width";
import { buildSpreadsheetColumnWidths, sanitizeSpreadsheetColumnWidths } from "@/helpers/spreadsheet-column-width";
import useLocalStorage from "@/hooks/use-local-storage";

const STORAGE_KEY = "spreadsheet_column_widths";

/**
 * Column widths of the spreadsheet layout, saved in the browser and shared by every spreadsheet (project,
 * module, cycle, view and workspace views). While a column is dragged the new widths are kept in state only;
 * they are written when the drag ends. With nothing saved the table keeps its automatic layout.
 */
export const useSpreadsheetColumnWidths = () => {
  const { storedValue, setValue } = useLocalStorage<TSpreadsheetColumnWidths>(STORAGE_KEY, {});
  const [draft, setDraft] = useState<TSpreadsheetColumnWidths | null>(null);

  const saved = useMemo(() => sanitizeSpreadsheetColumnWidths(storedValue), [storedValue]);

  const previewWidth = useCallback(
    (columnKey: string, width: number, measured: TSpreadsheetColumnWidths) =>
      setDraft(buildSpreadsheetColumnWidths(columnKey, width, measured)),
    []
  );

  const commitWidth = useCallback(
    (columnKey: string, width: number, measured: TSpreadsheetColumnWidths) => {
      setValue(buildSpreadsheetColumnWidths(columnKey, width, measured));
      setDraft(null);
    },
    [setValue]
  );

  const resetWidth = useCallback(
    (columnKey: string) => {
      const next = { ...saved };
      delete next[columnKey];
      setValue(next);
    },
    [saved, setValue]
  );

  return { widths: draft ?? saved, previewWidth, commitWidth, resetWidth };
};

export type TSpreadsheetColumnWidthControls = Pick<
  ReturnType<typeof useSpreadsheetColumnWidths>,
  "previewWidth" | "commitWidth" | "resetWidth"
>;
