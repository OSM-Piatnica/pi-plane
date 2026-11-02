/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
// plane imports
import type { TFilterableUserGroup } from "@plane/types";
// services
import { userGroupService } from "@/services/user-group.service";

const FILTERABLE_USER_GROUPS_KEY = (workspaceSlug: string) => `FILTERABLE_USER_GROUPS_${workspaceSlug}`;

/**
 * The groups the person may filter work items, modules and cycles by: every group of the workspace for an admin,
 * their own groups and the ones above them for everybody else. The API enforces the same limit on the filter itself.
 * `groups` is undefined while loading and when the request failed.
 */
export const useFilterableUserGroups = (workspaceSlug: string | undefined) => {
  const { data, isLoading } = useSWR<TFilterableUserGroup[]>(
    workspaceSlug ? FILTERABLE_USER_GROUPS_KEY(workspaceSlug) : null,
    workspaceSlug ? () => userGroupService.listFilterable(workspaceSlug) : null,
    { revalidateIfStale: false, revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { groups: data, isLoading };
};
