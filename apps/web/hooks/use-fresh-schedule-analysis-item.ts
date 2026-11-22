/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import type { TIssue, TScheduleAnalysisItem } from "@plane/types";
// helpers
import { getScheduleAnalysisItem, getScheduleAnalysisKey } from "@/helpers/schedule-analysis.helper";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useScheduleAnalysis } from "@/hooks/use-schedule-analysis";

type TOptions = {
  /**
   * Ask for a new analysis (of this project) when the work item changes. Leave it out where a loader of the layout
   * already does, such as the rows of a list: a row then only hides its stale value.
   */
  refreshProjectId?: string;
};

/**
 * The schedule analysis item of a work item, or undefined while nothing asks for the analysis (the critical path is
 * off, no Float column is shown) or the analysis in the store is stale for it. The analysis goes stale when this work
 * item's dates, state or relations change here. Answers to requests made before the change are not shown
 * (`staleUpTo`); others, such as a refresh of the timeline for another work item, keep what is shown in place instead
 * of blanking it while they load.
 */
export function useFreshScheduleAnalysisItem(issue: TIssue, options: TOptions = {}): TScheduleAnalysisItem | undefined {
  const { refreshProjectId } = options;
  const { isActive, scheduleAnalysis, scheduleAnalysisRequestId, scheduleAnalysisResultId, refreshScheduleAnalysis } =
    useScheduleAnalysis();
  const {
    relation: { relationMap, getRelationLag },
  } = useIssueDetail();

  const analysisKey = isActive ? getScheduleAnalysisKey([issue.id], () => issue, relationMap, getRelationLag) : "";
  const [tracked, setTracked] = useState({ issueId: issue.id, key: analysisKey, staleUpTo: 0 });
  if (tracked.issueId !== issue.id) {
    // another work item: the analysis in the store covers it as it is
    setTracked({ issueId: issue.id, key: analysisKey, staleUpTo: 0 });
  } else if (tracked.key !== analysisKey) {
    // the analysis starting to be asked for is no change of the work item
    const isChange = !!tracked.key && !!analysisKey;
    setTracked({ ...tracked, key: analysisKey, staleUpTo: isChange ? scheduleAnalysisRequestId : tracked.staleUpTo });
  }
  const changeId = tracked.staleUpTo;
  useEffect(() => {
    if (!changeId || !refreshProjectId) return;
    // a short wait lets the update of the work item reach the server first, and folds quick edits into one request;
    // a failed refresh clears the analysis in the store, so nothing stale is left to show
    const timeout = setTimeout(() => refreshScheduleAnalysis(refreshProjectId).catch(() => undefined), 500);
    return () => clearTimeout(timeout);
  }, [changeId, refreshProjectId, refreshScheduleAnalysis]);

  const isFresh = scheduleAnalysisResultId > tracked.staleUpTo;
  return isActive && isFresh ? getScheduleAnalysisItem(scheduleAnalysis, issue.id) : undefined;
}
