/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { CalendarClock, Hourglass } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssue, TScheduleAnalysisItem } from "@plane/types";
import { cn, renderFormattedDate } from "@plane/utils";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
// helpers
import { getScheduleAnalysisItem, getScheduleAnalysisKey } from "@/helpers/schedule-analysis.helper";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssuesTimeLineChart } from "@/hooks/use-timeline-chart";

type Props = {
  issue: TIssue;
  projectId: string;
};

/**
 * The schedule analysis item of a work item, or undefined while the critical path is off or the analysis in the store
 * is stale for it. The analysis goes stale when this work item's dates, state or relations change here. Answers to
 * requests made before the change are not shown (`staleUpTo`); others, such as a refresh of the timeline for another
 * work item, keep what is shown in place instead of blanking it while they load.
 */
function useFreshScheduleAnalysisItem(issue: TIssue, projectId: string): TScheduleAnalysisItem | undefined {
  const {
    isCriticalPathEnabled,
    scheduleAnalysis,
    scheduleAnalysisRequestId,
    scheduleAnalysisResultId,
    refreshScheduleAnalysis,
  } = useIssuesTimeLineChart();
  const {
    relation: { relationMap, getRelationLag },
  } = useIssueDetail();

  const analysisKey = isCriticalPathEnabled
    ? getScheduleAnalysisKey([issue.id], () => issue, relationMap, getRelationLag)
    : "";
  const [tracked, setTracked] = useState({ issueId: issue.id, key: analysisKey, staleUpTo: 0 });
  if (tracked.issueId !== issue.id) {
    // another work item: the analysis in the store covers it as it is
    setTracked({ issueId: issue.id, key: analysisKey, staleUpTo: 0 });
  } else if (tracked.key !== analysisKey) {
    // switching the critical path on is no change of the work item
    const isChange = !!tracked.key && !!analysisKey;
    setTracked({ ...tracked, key: analysisKey, staleUpTo: isChange ? scheduleAnalysisRequestId : tracked.staleUpTo });
  }
  const changeId = tracked.staleUpTo;
  useEffect(() => {
    if (!changeId) return;
    // a short wait lets the update of the work item reach the server first, and folds quick edits into one request;
    // a failed refresh clears the analysis in the store, so nothing stale is left to show
    const timeout = setTimeout(() => refreshScheduleAnalysis(projectId).catch(() => undefined), 500);
    return () => clearTimeout(timeout);
  }, [changeId, projectId, refreshScheduleAnalysis]);

  const isFresh = scheduleAnalysisResultId > tracked.staleUpTo;
  return isCriticalPathEnabled && isFresh ? getScheduleAnalysisItem(scheduleAnalysis, issue.id) : undefined;
}

const ScheduleInfoRows = observer(function ScheduleInfoRows({ item }: { item: TScheduleAnalysisItem }) {
  const { t } = useTranslation();
  const isCritical = item.is_critical;
  // dates are ISO "YYYY-MM-DD" strings, so they compare as text
  const isNeededByMissed = !!item.needed_by && item.earliest_finish > item.needed_by;

  return (
    <>
      <SidebarPropertyListItem icon={Hourglass} label={t("schedule_analysis.float")}>
        <span
          className={cn("px-2 text-body-xs-regular", isCritical ? "text-danger-primary" : "text-secondary")}
          title={t("schedule_analysis.float_help")}
          data-testid="work-item-float"
        >
          {isCritical
            ? t("schedule_analysis.float_critical")
            : t("schedule_analysis.float_days", { count: item.total_float })}
        </span>
      </SidebarPropertyListItem>
      {item.needed_by && (
        <SidebarPropertyListItem icon={CalendarClock} label={t("schedule_analysis.needed_by")}>
          <span
            className={cn("px-2 text-body-xs-regular", isNeededByMissed ? "text-danger-primary" : "text-secondary")}
            title={t("schedule_analysis.needed_by_help")}
            data-testid="work-item-needed-by"
          >
            {renderFormattedDate(item.needed_by)}
          </span>
        </SidebarPropertyListItem>
      )}
    </>
  );
});

/**
 * Float and "needed by" of a work item, read-only, from the critical path analysis of the timeline. Shown only while
 * the critical path is switched on and its analysis covers this work item (a truncated one covers none); a completed
 * or cancelled work item has neither. "Needed by" is red when the earliest finish, not only the planned one, is late.
 */
export const WorkItemScheduleInfo = observer(function WorkItemScheduleInfo(props: Props) {
  const { issue, projectId } = props;
  const item = useFreshScheduleAnalysisItem(issue, projectId);
  if (!item || item.is_fixed || item.total_float === null) return null;
  return <ScheduleInfoRows item={item} />;
});
