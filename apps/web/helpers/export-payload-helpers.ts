/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TWorkItemFilterExpression } from "@plane/types";

export type IssueExportProviderOption = {
  provider: string;
  delimiter?: "," | ";";
};

export type IssueExportFormPayload = {
  provider: IssueExportProviderOption;
  project: string[];
  filters: TWorkItemFilterExpression;
  /** The optional columns switched on, with every optional column that can be chosen. */
  columns?: { selected: string[]; available: string[] };
};

export function buildIssueExportPayload(formData: IssueExportFormPayload) {
  return {
    provider: formData.provider.provider,
    project: formData.project,
    multiple: formData.project.length > 1,
    rich_filters: formData.filters,
    // Everything switched on is sent as no choice, so a column the API adds later is exported too
    ...(formData.columns && !formData.columns.available.every((key) => formData.columns?.selected.includes(key))
      ? { fields: formData.columns.available.filter((key) => formData.columns?.selected.includes(key)) }
      : {}),
    ...(formData.provider.provider === "csv" && formData.provider.delimiter
      ? { delimiter: formData.provider.delimiter }
      : {}),
  };
}
