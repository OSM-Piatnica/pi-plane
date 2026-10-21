/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { MutableRefObject } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { observer } from "mobx-react";
// plane imports
import type { IIssueDisplayFilterOptions, IIssueDisplayProperties, TIssue } from "@plane/types";
import { cn } from "@plane/utils";
// components
import { SpreadsheetIssueRowLoader } from "@/components/ui/loader/layouts/spreadsheet-layout-loader";
// helpers
import { shouldRenderColumn } from "@/helpers/issue-filter.helper";
import {
  SPREADSHEET_COLUMN_DEFAULT_WIDTH,
  SPREADSHEET_WORK_ITEM_COLUMN_KEY,
  SPREADSHEET_WORK_ITEM_COLUMN_MIN_WIDTH,
} from "@/helpers/spreadsheet-column-width";
// hooks
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";
import { useIssuesStore } from "@/hooks/use-issue-layout-store";
import type { TSelectionHelper } from "@/hooks/use-multiple-select";
import { useSpreadsheetColumnWidths } from "@/hooks/use-spreadsheet-column-widths";
import { useTableKeyboardNavigation } from "@/hooks/use-table-keyboard-navigation";
// local imports
import type { TRenderQuickActions } from "../list/list-view-types";
import { getDisplayPropertiesCount } from "../utils";
import { SpreadsheetIssueRow } from "./issue-row";
import { SpreadsheetHeader } from "./spreadsheet-header";

type Props = {
  displayProperties: IIssueDisplayProperties;
  displayFilters: IIssueDisplayFilterOptions;
  handleDisplayFilterUpdate: (data: Partial<IIssueDisplayFilterOptions>) => void;
  issueIds: string[];
  isEstimateEnabled: boolean;
  quickActions: TRenderQuickActions;
  updateIssue: ((projectId: string | null, issueId: string, data: Partial<TIssue>) => Promise<void>) | undefined;
  canEditProperties: (projectId: string | undefined) => boolean;
  portalElement: React.MutableRefObject<HTMLDivElement | null>;
  containerRef: MutableRefObject<HTMLTableElement | null>;
  canLoadMoreIssues: boolean;
  loadMoreIssues: () => void;
  spreadsheetColumnsList: (keyof IIssueDisplayProperties)[];
  selectionHelpers: TSelectionHelper;
  isEpic?: boolean;
};

export const SpreadsheetTable = observer(function SpreadsheetTable(props: Props) {
  const {
    displayProperties,
    displayFilters,
    handleDisplayFilterUpdate,
    issueIds,
    isEstimateEnabled,
    portalElement,
    quickActions,
    updateIssue,
    canEditProperties,
    canLoadMoreIssues,
    containerRef,
    loadMoreIssues,
    spreadsheetColumnsList,
    selectionHelpers,
    isEpic = false,
  } = props;

  // states
  const isScrolled = useRef(false);
  const [intersectionElement, setIntersectionElement] = useState<HTMLTableSectionElement | null>(null);

  const {
    issues: { getIssueLoader },
  } = useIssuesStore();

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const scrollLeft = containerRef.current.scrollLeft;

    const columnShadow = "8px 22px 22px 10px rgba(0, 0, 0, 0.05)"; // shadow for regular columns
    const headerShadow = "8px -22px 22px 10px rgba(0, 0, 0, 0.05)"; // shadow for headers

    //The shadow styles are added this way to avoid re-render of all the rows of table, which could be costly
    if (scrollLeft > 0 !== isScrolled.current) {
      const firstColumns = containerRef.current.querySelectorAll("table tr td:first-child, th:first-child");

      for (let i = 0; i < firstColumns.length; i++) {
        const shadow = i === 0 ? headerShadow : columnShadow;
        if (scrollLeft > 0) {
          (firstColumns[i] as HTMLElement).style.boxShadow = shadow;
        } else {
          (firstColumns[i] as HTMLElement).style.boxShadow = "none";
        }
      }
      isScrolled.current = scrollLeft > 0;
    }
  }, [containerRef]);

  useEffect(() => {
    const currentContainerRef = containerRef.current;

    if (currentContainerRef) currentContainerRef.addEventListener("scroll", handleScroll);

    return () => {
      if (currentContainerRef) currentContainerRef.removeEventListener("scroll", handleScroll);
    };
  }, [handleScroll, containerRef]);

  const isPaginating = !!getIssueLoader();

  useIntersectionObserver(containerRef, isPaginating ? null : intersectionElement, loadMoreIssues, `100% 0% 100% 0%`);

  const handleKeyBoardNavigation = useTableKeyboardNavigation();

  const ignoreFieldsForCounting: (keyof IIssueDisplayProperties)[] = ["key"];
  if (!isEstimateEnabled) ignoreFieldsForCounting.push("estimate");
  const displayPropertiesCount = getDisplayPropertiesCount(displayProperties, ignoreFieldsForCounting);

  // Column widths saved in the browser. Until one is saved the table keeps its automatic layout; after the first
  // resize every column has a width and the table is laid out with them (a fixed layout).
  const { widths, ...columnWidthControls } = useSpreadsheetColumnWidths();
  const hasCustomWidths = Object.keys(widths).length > 0;
  const visibleColumns = spreadsheetColumnsList.filter(
    (property) => !!displayProperties[property] && shouldRenderColumn(property)
  );
  const workItemColumnWidth = widths[SPREADSHEET_WORK_ITEM_COLUMN_KEY];
  const tableMinWidth =
    (workItemColumnWidth ?? SPREADSHEET_WORK_ITEM_COLUMN_MIN_WIDTH) +
    visibleColumns.reduce((total, property) => total + (widths[property] ?? SPREADSHEET_COLUMN_DEFAULT_WIDTH), 0);

  return (
    <table
      className={cn("w-full overflow-y-auto bg-surface-1", {
        // cells must clip their content once the columns have a fixed width
        "[&_td]:overflow-hidden [&_th]:overflow-hidden": hasCustomWidths,
      })}
      style={hasCustomWidths ? { tableLayout: "fixed", minWidth: tableMinWidth } : undefined}
      onKeyDown={handleKeyBoardNavigation}
    >
      {hasCustomWidths && (
        <colgroup>
          {/* the work item column takes the remaining space until it is resized itself */}
          <col style={workItemColumnWidth ? { width: workItemColumnWidth } : undefined} />
          {visibleColumns.map((property) => (
            <col key={property} style={{ width: widths[property] ?? SPREADSHEET_COLUMN_DEFAULT_WIDTH }} />
          ))}
        </colgroup>
      )}
      <SpreadsheetHeader
        displayProperties={displayProperties}
        displayFilters={displayFilters}
        handleDisplayFilterUpdate={handleDisplayFilterUpdate}
        canEditProperties={canEditProperties}
        isEstimateEnabled={isEstimateEnabled}
        spreadsheetColumnsList={spreadsheetColumnsList}
        selectionHelpers={selectionHelpers}
        isEpic={isEpic}
        columnWidthControls={columnWidthControls}
      />
      <tbody>
        {issueIds.map((id) => (
          <SpreadsheetIssueRow
            key={id}
            issueId={id}
            displayProperties={displayProperties}
            quickActions={quickActions}
            canEditProperties={canEditProperties}
            nestingLevel={0}
            isEstimateEnabled={isEstimateEnabled}
            updateIssue={updateIssue}
            portalElement={portalElement}
            containerRef={containerRef}
            isScrolled={isScrolled}
            spreadsheetColumnsList={spreadsheetColumnsList}
            selectionHelpers={selectionHelpers}
            isEpic={isEpic}
          />
        ))}
      </tbody>
      {canLoadMoreIssues && (
        <tfoot ref={setIntersectionElement}>
          {Array.from({ length: 3 }).map((_, index) => (
            // oxlint-disable-next-line react/no-array-index-key -- no stable unique key available
            <SpreadsheetIssueRowLoader key={index} columnCount={displayPropertiesCount} />
          ))}
        </tfoot>
      )}
    </table>
  );
});
