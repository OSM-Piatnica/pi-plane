/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TProjectMemberExportFormat, TProjectMemberExportParams } from "@plane/types";

type TExporterChoice = { provider: TProjectMemberExportFormat; delimiter?: "," | ";" };

/** The query of the members export for the format choice of the form (the delimiter only matters for CSV). */
export const buildMemberExportParams = (
  choice: TExporterChoice,
  includeViaGroup: boolean
): TProjectMemberExportParams => {
  const params: TProjectMemberExportParams = {
    format: choice.provider,
    include_via_group: includeViaGroup ? 1 : 0,
  };
  if (choice.provider === "csv") params.delimiter = choice.delimiter ?? ",";
  return params;
};

/** The file name the API sent in Content-Disposition, or the fallback when it sent none. */
export const filenameFromContentDisposition = (header: string | undefined | null, fallback: string): string => {
  const match = /filename="?([^";]+)"?/i.exec(header ?? "");
  const name = match?.[1]?.trim();
  return name ? name : fallback;
};
