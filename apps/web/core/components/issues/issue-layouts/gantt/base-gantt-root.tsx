/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React, { useCallback, useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { ALL_ISSUES, EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { EIssuesStoreType, IBlockUpdateData, IBlockUpdateDependencyData, TIssue } from "@plane/types";
import { EIssueLayoutTypes, GANTT_TIMELINE_TYPE } from "@plane/types";
import { renderFormattedPayloadDate, validateWorkItemSchedule } from "@plane/utils";
// components
import { TimeLineTypeContext } from "@/components/gantt-chart/contexts";
import { GanttChartRoot } from "@/components/gantt-chart/root";
import { IssueGanttSidebar } from "@/components/gantt-chart/sidebar/issues/sidebar";
// helpers
import { wouldUpdatesViolateDependencies } from "@/helpers/gantt-dependency-helpers";
import { getIssueApiErrorMessage } from "@/helpers/issue-api-error";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useUserPermissions } from "@/hooks/store/user";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import { useIssuesActions } from "@/hooks/use-issues-actions";
import { useTimeLineChart } from "@/hooks/use-timeline-chart";
// plane web hooks
import { useBulkOperationStatus } from "@/plane-web/hooks/use-bulk-operation-status";

import { IssueLayoutHOC } from "../issue-layout-HOC";
import { GanttQuickAddIssueButton, QuickAddIssueRoot } from "../quick-add";
import { IssueGanttBlock } from "./blocks";

interface IBaseGanttRoot {
  viewId?: string | undefined;
  isCompletedCycle?: boolean;
  isEpic?: boolean;
}

type TWorkItemDatesUpdate = { id: string; start_date?: string; finish_date?: string; target_date?: string };

export type GanttStoreType =
  | EIssuesStoreType.PROJECT
  | EIssuesStoreType.MODULE
  | EIssuesStoreType.CYCLE
  | EIssuesStoreType.PROJECT_VIEW
  | EIssuesStoreType.EPIC;

export const BaseGanttRoot = observer(function BaseGanttRoot(props: IBaseGanttRoot) {
  const { viewId, isCompletedCycle = false, isEpic = false } = props;
  const { t } = useTranslation();
  // router
  const { workspaceSlug, projectId } = useParams();

  const storeType = useIssueStoreType() as GanttStoreType;
  const { issues, issuesFilter } = useIssues(storeType);
  const { fetchIssues, fetchNextIssues, updateIssue, quickAddIssue } = useIssuesActions(storeType);
  const { initGantt, refreshBlockPositions } = useTimeLineChart(GANTT_TIMELINE_TYPE.ISSUE);
  // store hooks
  const { allowPermissions } = useUserPermissions();

  const appliedDisplayFilters = issuesFilter.issueFilters?.displayFilters;
  // plane web hooks
  const isBulkOperationsEnabled = useBulkOperationStatus();
  // derived values
  const targetDate = new Date();
  targetDate.setDate(targetDate.getDate() + 1);

  useEffect(() => {
    fetchIssues("init-loader", { canGroup: false, perPageCount: 100 }, viewId);
  }, [fetchIssues, storeType, viewId]);

  useEffect(() => {
    initGantt();
  }, [initGantt]);

  const issuesIds = (issues.groupedIssueIds?.[ALL_ISSUES] as string[]) ?? [];
  const nextPageResults = issues.getPaginationData(undefined, undefined)?.nextPageResults;

  const { enableIssueCreation } = issues?.viewFlags || {};

  const loadMoreIssues = useCallback(() => {
    fetchNextIssues();
  }, [fetchNextIssues]);

  const updateIssueBlockStructure = async (issue: TIssue, data: IBlockUpdateData) => {
    if (!workspaceSlug) return;

    const { target_date: barEnd, ...rest } = data;
    const payload: any = { ...rest };
    if (data.sort_order) payload.sort_order = data.sort_order.newSortOrder;
    // the generic gantt block's `target_date` is the bar end, which for a work item is its finish date.
    // The work item's own `target_date` (due date) is never written from the bar.
    if (barEnd !== undefined) payload.finish_date = barEnd;

    if (updateIssue) {
      await updateIssue(issue.project_id, issue.id, payload);
    }
  };

  const isAllowed = allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.PROJECT);
  const updateBlockDates = useCallback(
    async (blockUpdates: IBlockUpdateDependencyData[]) => {
      const {
        relation,
        issue: { getIssueById },
      } = issues.rootIssueStore.issueDetail;

      // Translate the generic bar (`start_date`, `target_date` = bar end) into a work item's own dates:
      // the bar end is the finish date, and only the deadline marker (`due_date`) writes the due date.
      const updates: TWorkItemDatesUpdate[] = blockUpdates.map((update) => ({
        id: update.id,
        ...(update.start_date !== undefined && { start_date: update.start_date }),
        ...(update.target_date !== undefined && { finish_date: update.target_date }),
        ...(update.due_date !== undefined && { target_date: update.due_date }),
      }));

      const hasScheduleChange = (update: TWorkItemDatesUpdate) =>
        update.start_date !== undefined || update.finish_date !== undefined;

      // finish must never precede start; due is not part of this check
      const endsBeforeStart = updates.some((update) => {
        if (!hasScheduleChange(update)) return false;
        const issue = getIssueById(update.id);
        return !!validateWorkItemSchedule(
          update.start_date ?? issue?.start_date,
          update.finish_date ?? issue?.finish_date
        );
      });

      if (endsBeforeStart) {
        refreshBlockPositions();
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("toast.error"),
          message: t("issue.dates.finish_before_start"),
        });
        return;
      }

      // a due-only change never touches dependencies
      const scheduleUpdates = updates.filter(hasScheduleChange);
      const violatesDependencies = wouldUpdatesViolateDependencies(scheduleUpdates, relation.relationMap, (issueId) => {
        const issue = getIssueById(issueId);
        return issue ? { start_date: issue.start_date, finish_date: issue.finish_date } : undefined;
      });

      if (violatesDependencies) {
        refreshBlockPositions();
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("toast.error"),
          message: t("issue.relation.date_conflict"),
        });
        return;
      }

      return issues.updateIssueDates(workspaceSlug.toString(), updates, projectId.toString()).catch((error) => {
        // The pre-check above only sees relations of the blocks currently on screen, so a
        // conflict with a work item outside the view reaches us as a rejection from the server.
        refreshBlockPositions();
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("toast.error"),
          message: getIssueApiErrorMessage(error, t("issue.relation.date_conflict"), t),
        });
      });
    },
    [issues, projectId, workspaceSlug, t, refreshBlockPositions]
  );

  const quickAdd =
    enableIssueCreation && isAllowed && !isCompletedCycle ? (
      <QuickAddIssueRoot
        layout={EIssueLayoutTypes.GANTT}
        QuickAddButton={GanttQuickAddIssueButton}
        containerClassName="sticky bottom-0 z-[1]"
        prePopulatedData={{
          start_date: renderFormattedPayloadDate(new Date()),
          finish_date: renderFormattedPayloadDate(targetDate),
        }}
        quickAddCallback={quickAddIssue}
        isEpic={isEpic}
      />
    ) : undefined;

  return (
    <IssueLayoutHOC layout={EIssueLayoutTypes.GANTT}>
      <TimeLineTypeContext.Provider value={GANTT_TIMELINE_TYPE.ISSUE}>
        <div className="h-full w-full">
          <GanttChartRoot
            border={false}
            title={isEpic ? t("epic.label", { count: 2 }) : t("issue.label", { count: 2 })}
            loaderTitle={isEpic ? t("epic.label", { count: 2 }) : t("issue.label", { count: 2 })}
            blockIds={issuesIds}
            blockUpdateHandler={updateIssueBlockStructure}
            blockToRender={(data: TIssue) => <IssueGanttBlock issueId={data.id} isEpic={isEpic} />}
            sidebarToRender={(sidebarProps) => <IssueGanttSidebar {...sidebarProps} showAllBlocks isEpic={isEpic} />}
            enableBlockLeftResize={isAllowed}
            enableBlockRightResize={isAllowed}
            enableBlockMove={isAllowed}
            enableReorder={appliedDisplayFilters?.order_by === "sort_order" && isAllowed}
            enableAddBlock={isAllowed}
            enableSelection={isBulkOperationsEnabled && isAllowed}
            quickAdd={quickAdd}
            loadMoreBlocks={loadMoreIssues}
            canLoadMoreBlocks={nextPageResults}
            updateBlockDates={updateBlockDates}
            showAllBlocks
            enableDependency
            isEpic={isEpic}
          />
        </div>
      </TimeLineTypeContext.Provider>
    </IssueLayoutHOC>
  );
});
