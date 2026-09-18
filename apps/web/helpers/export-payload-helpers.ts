/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
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
};

export function buildIssueExportPayload(formData: IssueExportFormPayload) {
  return {
    provider: formData.provider.provider,
    project: formData.project,
    multiple: formData.project.length > 1,
    rich_filters: formData.filters,
    ...(formData.provider.provider === "csv" && formData.provider.delimiter
      ? { delimiter: formData.provider.delimiter }
      : {}),
  };
}
