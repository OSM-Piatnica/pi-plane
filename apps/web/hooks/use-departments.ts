/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import useSWR from "swr";
// plane imports
import type { TDepartment } from "@plane/types";
// helpers
import { getAllDepartmentsKey } from "@/helpers/department";
// services
import { userGroupService } from "@/services/user-group.service";

const EMPTY: TDepartment[] = [];

/**
 * Every department of the workspace, the ones that are switched off included (`is_active` tells them apart):
 * a work item may still name such a department in its RACI. Nothing is fetched while `enabled` is false.
 */
export const useDepartments = (workspaceSlug: string | undefined, enabled: boolean = true) => {
  const { data, isLoading } = useSWR<TDepartment[]>(
    enabled && workspaceSlug ? getAllDepartmentsKey(workspaceSlug) : null,
    workspaceSlug ? () => userGroupService.listDepartments(workspaceSlug, true) : null,
    { revalidateIfStale: false, revalidateOnFocus: false, shouldRetryOnError: false }
  );
  const departments = data ?? EMPTY;
  const departmentsById = useMemo(
    () => new Map(departments.map((department) => [department.id, department])),
    [departments]
  );
  return { departments, departmentsById, isLoading };
};
