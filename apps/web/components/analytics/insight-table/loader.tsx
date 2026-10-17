/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import * as React from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@plane/propel/table";
import { Loader } from "@plane/ui";

interface TableSkeletonProps {
  columns: ColumnDef<any>[];
  rows: number;
}

export function TableLoader({ columns, rows }: TableSkeletonProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column, index) => (
            // oxlint-disable-next-line react/no-array-index-key -- no stable unique key available
            <TableHead key={column.header?.toString() ?? index}>
              {typeof column.header === "string" ? column.header : ""}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          // oxlint-disable-next-line react/no-array-index-key -- no stable unique key available
          <TableRow key={rowIndex}>
            {columns.map((_column, colIndex) => (
              // oxlint-disable-next-line react/no-array-index-key -- no stable unique key available
              <TableCell key={colIndex}>
                <Loader.Item height="20px" width="100%" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
