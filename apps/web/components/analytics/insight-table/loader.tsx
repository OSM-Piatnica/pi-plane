/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import * as React from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@makeplane/propel/components/table";
import { Loader } from "@plane/blocks/skeleton";

interface TableSkeletonProps {
  columns: ColumnDef<any>[];
  rows: number;
}

const getColumnKey = (column: ColumnDef<any>) => column.id ?? String(column.header ?? "");

export function TableLoader({ columns, rows }: TableSkeletonProps) {
  const rowKeys = Array.from({ length: rows }, (_, rowIndex) => `skeleton-row-${rowIndex}`);

  return (
    <Table variant="table">
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            // oxlint-disable-next-line react/no-array-index-key -- no stable unique key available
            <TableHead
              key={getColumnKey(column)}
              pinned="none"
              label={typeof column.header === "string" ? column.header : ""}
            />
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rowKeys.map((rowKey) => (
          <TableRow key={rowKey}>
            {columns.map((column) => (
              <TableCell key={getColumnKey(column)} pinned="none" padding="cell">
                <Loader.Item height="20px" width="100%" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
