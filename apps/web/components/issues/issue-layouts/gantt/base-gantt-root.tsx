/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { ALL_ISSUES, EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
import type { EIssuesStoreType, IBlockUpdateData, TIssue } from "@plane/types";
import { EIssueLayoutTypes, GANTT_TIMELINE_TYPE } from "@plane/types";
import { renderFormattedPayloadDate } from "@plane/utils";
// components
import { GanttSubWorkItemsContext, TimeLineTypeContext } from "@/components/gantt-chart/contexts";
import { GanttChartRoot } from "@/components/gantt-chart/root";
import { IssueGanttSidebar } from "@/components/gantt-chart/sidebar/issues/sidebar";
// helpers
import { wouldUpdatesViolateDependencies } from "@/helpers/gantt-dependency-helpers";
import type { TGanttExpansion } from "@/helpers/gantt-sub-work-items.helper";
import {
  DEFAULT_GANTT_EXPANSION,
  flattenGanttRows,
  isGanttRowExpanded,
  showGanttLevels,
  toggleGanttRow,
} from "@/helpers/gantt-sub-work-items.helper";
import { getIssueApiErrorMessage } from "@/helpers/issue-api-error";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssues } from "@/hooks/store/use-issues";
import { useUserPermissions } from "@/hooks/store/user";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import { useIssuesActions } from "@/hooks/use-issues-actions";
import useLocalStorage from "@/hooks/use-local-storage";
import { useIssuesTimeLineChart, useTimeLineChart } from "@/hooks/use-timeline-chart";
import { useBulkOperationStatus } from "@/hooks/use-bulk-operation-status";

import { IssueLayoutHOC } from "../issue-layout-HOC";
import { GanttQuickAddIssueButton, QuickAddIssueRoot } from "../quick-add";
import { IssueGanttBlock } from "./blocks";
import { GanttHierarchyControls } from "./hierarchy-controls";
import { GanttRollupToggle } from "./rollup-toggle";

interface IBaseGanttRoot {
  viewId?: string | undefined;
  isCompletedCycle?: boolean;
  isEpic?: boolean;
}

const NO_ISSUE_IDS: string[] = [];
const NEVER_EXPANDED = () => false;
// Unfolding many levels at once loads the sub-work items of every parent, a few requests at a time and not beyond a cap
const MAX_PARALLEL_FETCHES = 4;
const MAX_FETCHES_PER_CHOICE = 200;

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
  const { isDateRollupEnabled, fetchDateRollups } = useIssuesTimeLineChart();
  // store hooks
  const { allowPermissions } = useUserPermissions();
  const {
    issue: { getIssueById: getWorkItemById },
    subIssues: { subIssuesByIssueId, fetchSubIssues },
  } = useIssueDetail();
  // how far the sub-work items below their parent are unfolded, per person and per view
  const { storedValue: storedExpansion, setValue: setExpansion } = useLocalStorage<TGanttExpansion>(
    `timeline_hierarchy_${workspaceSlug}_${projectId}_${viewId ?? storeType}`,
    DEFAULT_GANTT_EXPANSION
  );
  const expansion = storedExpansion ?? DEFAULT_GANTT_EXPANSION;
  // the parents whose sub-work items are being loaded; the ones that failed are not tried again until the next choice
  const [loadingIds, setLoadingIds] = useState<ReadonlySet<string>>(() => new Set());
  const failedIdsRef = useRef<Set<string>>(new Set());
  const fetchCountRef = useRef(0);
  const reportedLimitRef = useRef(false);

  const appliedDisplayFilters = issuesFilter.issueFilters?.displayFilters;
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

  const listedIssueIds = (issues.groupedIssueIds?.[ALL_ISSUES] as string[] | undefined) ?? NO_ISSUE_IDS;
  // When the display option "show sub-work items" is on, the sub-work items are listed in their own rows already.
  const canExpandSubWorkItems = !appliedDisplayFilters?.sub_issue;
  const rows = flattenGanttRows(
    listedIssueIds,
    canExpandSubWorkItems ? (id, level) => isGanttRowExpanded(expansion, id, level) : NEVER_EXPANDED,
    subIssuesByIssueId
  );
  // the rows as a primitive, so that what depends on them only changes when a row does
  const rowsKey = rows.ids.map((id) => `${id}:${rows.levelById[id]}`).join(",");
  const { issuesIds, levelById } = useMemo(
    () => ({ issuesIds: rows.ids, levelById: rows.levelById }),
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- rowsKey stands for the ids and levels
    [rowsKey]
  );
  const expandedIds = rows.expandedIds;

  // Parents show the dates of the work items below them. Fetched when a loaded work item moves, is re-parented, changes
  // dates or gets a child: the key stands for what the rollups depend on.
  const parentIds = issuesIds.filter((id) => (getWorkItemById(id)?.sub_issues_count ?? 0) > 0);
  const rollupKey = issuesIds
    .map((id) => {
      const workItem = getWorkItemById(id);
      return `${id}|${workItem?.parent_id}|${workItem?.start_date}|${workItem?.target_date}|${workItem?.sub_issues_count}`;
    })
    .join(";");
  useEffect(() => {
    if (!isDateRollupEnabled || !workspaceSlug || !projectId || parentIds.length === 0) return;
    const timeout = setTimeout(() => {
      fetchDateRollups(workspaceSlug.toString(), projectId.toString(), parentIds).catch(() => undefined);
    }, 250);
    return () => clearTimeout(timeout);
    // parentIds comes from the same inputs as rollupKey
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [rollupKey, isDateRollupEnabled, workspaceSlug, projectId, fetchDateRollups]);

  // a new choice of levels or rows starts afresh: failed parents may be tried again
  useEffect(() => {
    failedIdsRef.current = new Set();
    fetchCountRef.current = 0;
    reportedLimitRef.current = false;
  }, [expansion]);

  // load the sub-work items of the parents that are unfolded but not loaded yet
  const pendingIds = rows.unloadedExpandedIds.filter(
    (id) => (getWorkItemById(id)?.sub_issues_count ?? 0) > 0 && !loadingIds.has(id) && !failedIdsRef.current.has(id)
  );
  const pendingKey = pendingIds.join(",");
  useEffect(() => {
    if (!workspaceSlug || pendingIds.length === 0) return;
    let freeSlots = MAX_PARALLEL_FETCHES - loadingIds.size;
    for (const workItemId of pendingIds) {
      if (freeSlots <= 0) break;
      if (fetchCountRef.current >= MAX_FETCHES_PER_CHOICE) {
        if (!reportedLimitRef.current) {
          reportedLimitRef.current = true;
          setToast({ type: "info", title: t("info"), message: t("timeline_hierarchy.too_many") });
        }
        break;
      }
      const workItem = getWorkItemById(workItemId);
      if (!workItem) continue;
      freeSlots -= 1;
      fetchCountRef.current += 1;
      setLoadingIds((current) => new Set(current).add(workItemId));
      fetchSubIssues(workspaceSlug.toString(), workItem.project_id ?? projectId?.toString() ?? "", workItemId)
        .catch(() => {
          // leave the row folded so that its chevron can be used again
          failedIdsRef.current.add(workItemId);
          setExpansion(toggleGanttRow(expansion, workItemId, true));
          setToast({ type: "error", title: t("toast.error"), message: t("timeline_hierarchy.load_error") });
        })
        .finally(() => setLoadingIds((current) => new Set([...current].filter((id) => id !== workItemId))));
    }
    // pendingKey stands for pendingIds; loadingIds frees the slots
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingKey, loadingIds, workspaceSlug]);

  const toggleSubWorkItems = useCallback(
    (workItemId: string) => {
      failedIdsRef.current.delete(workItemId);
      setExpansion(toggleGanttRow(expansion, workItemId, expandedIds.has(workItemId)));
    },
    [expansion, expandedIds, setExpansion]
  );

  const subWorkItems = useMemo(
    () => (canExpandSubWorkItems ? { levelById, expandedIds, loadingIds, toggle: toggleSubWorkItems } : undefined),
    [canExpandSubWorkItems, levelById, expandedIds, loadingIds, toggleSubWorkItems]
  );
  const nextPageResults = issues.getPaginationData(undefined, undefined)?.nextPageResults;

  const { enableIssueCreation } = issues?.viewFlags || {};

  const loadMoreIssues = useCallback(() => {
    fetchNextIssues();
  }, [fetchNextIssues]);

  const updateIssueBlockStructure = async (issue: TIssue, data: IBlockUpdateData) => {
    if (!workspaceSlug) return;

    const payload: any = { ...data };
    if (data.sort_order) payload.sort_order = data.sort_order.newSortOrder;

    if (updateIssue) {
      await updateIssue(issue.project_id, issue.id, payload);
    }
  };

  const isAllowed = allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.PROJECT);
  const updateBlockDates = useCallback(
    async (
      updates: {
        id: string;
        start_date?: string;
        target_date?: string;
      }[]
    ) => {
      const {
        relation,
        issue: { getIssueById },
      } = issues.rootIssueStore.issueDetail;

      const violatesDependencies = wouldUpdatesViolateDependencies(updates, relation.relationMap, (issueId) => {
        const issue = getIssueById(issueId);
        return issue ? { start_date: issue.start_date, target_date: issue.target_date } : undefined;
      });

      if (violatesDependencies) {
        refreshBlockPositions();
        setToast({
          type: "error",
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
          type: "error",
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
          target_date: renderFormattedPayloadDate(targetDate),
        }}
        quickAddCallback={quickAddIssue}
        isEpic={isEpic}
      />
    ) : undefined;

  return (
    <IssueLayoutHOC layout={EIssueLayoutTypes.GANTT}>
      <TimeLineTypeContext.Provider value={GANTT_TIMELINE_TYPE.ISSUE}>
        <GanttSubWorkItemsContext.Provider value={subWorkItems}>
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
              headerActions={
                <>
                  {canExpandSubWorkItems && (
                    <GanttHierarchyControls
                      depth={expansion.depth}
                      onShowLevels={(depth) => setExpansion(showGanttLevels(depth))}
                    />
                  )}
                  <GanttRollupToggle />
                </>
              }
            />
          </div>
        </GanttSubWorkItemsContext.Provider>
      </TimeLineTypeContext.Provider>
    </IssueLayoutHOC>
  );
});
