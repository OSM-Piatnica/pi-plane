/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import type { TProjectIssueType } from "@plane/types";
import { getDefaultProjectIssueTypeId } from "@/helpers/issue-type-options";
import { IssueTypeService } from "@/services/issue-type.service";

const service = new IssueTypeService();

export function useProjectIssueTypes(workspaceSlug: string | undefined, projectId: string | null | undefined) {
  const key = workspaceSlug && projectId ? `PROJECT_ISSUE_TYPES_${workspaceSlug}_${projectId}` : null;
  const { data, error, isLoading, mutate } = useSWR(key, () => service.listProjectTypes(workspaceSlug!, projectId!));

  const types = (data ?? []) as TProjectIssueType[];

  return {
    types,
    // never a system-managed type: a person cannot create those work items by hand
    defaultTypeId: getDefaultProjectIssueTypeId(types),
    isLoading,
    error,
    mutate,
  };
}
