/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import type { TIssueType } from "@plane/types";
import { getSystemManagedTypeNames } from "@/helpers/issue-type-options";
import { IssueTypeService } from "@/services/issue-type.service";

const service = new IssueTypeService();

export function useWorkspaceIssueTypes(workspaceSlug: string | undefined, activeOnly = true) {
  const key = workspaceSlug ? `WORKSPACE_ISSUE_TYPES_${workspaceSlug}_${activeOnly}` : null;
  const { data, error, isLoading, mutate } = useSWR(key, () => service.listWorkspaceTypes(workspaceSlug!, activeOnly));

  const types = (data ?? []) as TIssueType[];
  const typeMap = Object.fromEntries(types.map((row) => [row.id, row]));

  return {
    types,
    typeMap,
    isLoading,
    error,
    mutate,
  };
}

/**
 * The names of the workspace's system-managed types, inactive ones included: the server finds a template's type by
 * name whether it is active or not. Loaded only when ``enabled``.
 */
export function useSystemManagedTypeNames(workspaceSlug: string | undefined, enabled: boolean): string[] {
  const { types } = useWorkspaceIssueTypes(enabled ? workspaceSlug : undefined, false);
  return getSystemManagedTypeNames(types);
}
