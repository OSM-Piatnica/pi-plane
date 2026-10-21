/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef } from "react";
//types
import { observer } from "mobx-react";
import type { IIssueDisplayFilterOptions, IIssueDisplayProperties } from "@plane/types";
//components
import { shouldRenderColumn } from "@/helpers/issue-filter.helper";
import type { TSpreadsheetColumnWidthControls } from "@/hooks/use-spreadsheet-column-widths";
import { WithDisplayPropertiesHOC } from "../properties/with-display-properties-HOC";
import { ColumnResizer, SPREADSHEET_COLUMN_KEY_ATTRIBUTE } from "./column-resizer";
import { HeaderColumn } from "./columns/header-column";

interface Props {
  displayProperties: IIssueDisplayProperties;
  property: keyof IIssueDisplayProperties;
  isEstimateEnabled: boolean;
  displayFilters: IIssueDisplayFilterOptions;
  handleDisplayFilterUpdate: (data: Partial<IIssueDisplayFilterOptions>) => void;
  isEpic?: boolean;
  columnWidthControls: TSpreadsheetColumnWidthControls;
}
export const SpreadsheetHeaderColumn = observer(function SpreadsheetHeaderColumn(props: Props) {
  const {
    displayProperties,
    displayFilters,
    property,
    handleDisplayFilterUpdate,
    isEpic = false,
    columnWidthControls,
  } = props;

  //hooks
  const tableHeaderCellRef = useRef<HTMLTableCellElement | null>(null);

  const shouldRenderProperty = shouldRenderColumn(property);

  return (
    <WithDisplayPropertiesHOC
      displayProperties={displayProperties}
      displayPropertyKey={property}
      shouldRenderProperty={() => shouldRenderProperty}
    >
      <th
        className="relative h-11 min-w-36 items-center border border-t-0 border-b-0 border-subtle bg-layer-1 py-1 text-13 font-medium"
        ref={tableHeaderCellRef}
        tabIndex={0}
        {...{ [SPREADSHEET_COLUMN_KEY_ATTRIBUTE]: property }}
      >
        <HeaderColumn
          displayFilters={displayFilters}
          handleDisplayFilterUpdate={handleDisplayFilterUpdate}
          property={property}
          onClose={() => {
            tableHeaderCellRef?.current?.focus();
          }}
          isEpic={isEpic}
        />
        <ColumnResizer columnKey={property} {...columnWidthControls} />
      </th>
    </WithDisplayPropertiesHOC>
  );
});
