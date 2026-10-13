/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import type { TIssue } from "@plane/types";
import type { TWorkItemDateStatuses, TWorkItemPlanningDates } from "@plane/utils";
import { getTodayInTimeZone, getWorkItemDateStatuses, planWorkItemDateChange } from "@plane/utils";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useWorkspace } from "@/hooks/store/use-workspace";

/**
 * Project time zone (workspace time zone as fallback): the zone that defines "today" and the end of
 * the due day for every viewer.
 */
export const useProjectTimeZone = (projectId: string | null | undefined) => {
  const { getProjectById } = useProject();
  const { currentWorkspace } = useWorkspace();
  return (projectId ? getProjectById(projectId)?.timezone : undefined) || currentWorkspace?.timezone || undefined;
};

/**
 * Derived date statuses (overdue, forecast misses deadline, ...) for a work item, in the project's
 * calendar. Completed and cancelled items are not active.
 */
export const useWorkItemDateStatuses = (
  issue: Pick<TIssue, "finish_date" | "target_date" | "completed_at" | "due_date_at_completion">,
  isActive: boolean,
  projectId: string | null | undefined
): TWorkItemDateStatuses => {
  const timeZone = useProjectTimeZone(projectId);
  return getWorkItemDateStatuses({
    finishDate: issue.finish_date,
    dueDate: issue.target_date,
    today: getTodayInTimeZone(timeZone),
    isActive,
    completedOn: issue.completed_at ? getTodayInTimeZone(timeZone, new Date(issue.completed_at)) : null,
    dueAtCompletion: issue.due_date_at_completion,
  });
};

/**
 * Edits start/finish/due through the shared date rules: duration follows the schedule, finish before
 * start is rejected (nothing is saved or moved), and the first manual finish/due entry fills the
 * other once (the server decides and the user is told, with Undo).
 *
 * The caller's `update` is the surface's existing save operation, so optimistic state, rollback and
 * error toasts stay where they were.
 */
export const useWorkItemDateEdit = (
  issue: Pick<TIssue, "start_date" | "finish_date" | "target_date" | "duration" | "dates_initialized">,
  update: (data: Partial<TIssue>) => Promise<void> | void
) => {
  const { t } = useTranslation();

  return useCallback(
    async (change: Partial<TWorkItemPlanningDates>, options?: { initialize?: boolean }) => {
      const { patch, error } = planWorkItemDateChange(issue, change, options?.initialize ?? true);
      if (error) {
        setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: t("issue.dates.finish_before_start") });
        return;
      }
      await update(patch as Partial<TIssue>);
    },
    [issue, update, t]
  );
};
