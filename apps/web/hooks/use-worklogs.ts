/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import { worklogService } from "@/services/issue/worklog.service";

/** The time logged on a work item, with its total; nothing is fetched while `enabled` is false. */
export const useWorklogs = (workspaceSlug: string, projectId: string, issueId: string, enabled: boolean = true) => {
  const { data, isLoading, mutate } = useSWR(
    enabled && workspaceSlug && projectId && issueId ? `ISSUE_WORKLOGS_${workspaceSlug}_${projectId}_${issueId}` : null,
    () => worklogService.getWorklogs(workspaceSlug, projectId, issueId),
    { revalidateOnFocus: false }
  );

  return {
    worklogs: data?.worklogs ?? [],
    totalDuration: data?.total_duration ?? 0,
    isLoading,
    mutate,
  };
};
