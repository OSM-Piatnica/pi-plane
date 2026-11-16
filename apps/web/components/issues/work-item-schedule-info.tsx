/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
import { observer } from "mobx-react";
import { CalendarClock, Hourglass } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
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
 * Float and "needed by" of a work item, read-only, from the critical path analysis of the timeline. Shown only while
 * the critical path is switched on and its analysis covers this work item; a completed or cancelled work item has
 * neither.
 */
export const WorkItemScheduleInfo = observer(function WorkItemScheduleInfo(props: Props) {
  const { issue, projectId } = props;
  const { t } = useTranslation();
  const { isCriticalPathEnabled, scheduleAnalysis, isScheduleAnalysisLoading, refreshScheduleAnalysis } =
    useIssuesTimeLineChart();
  const {
    relation: { relationMap, getRelationLag },
  } = useIssueDetail();

  // The analysis goes stale when this work item's dates, state or relations change here: ask for it again. The first
  // render only remembers the key, as the analysis in the store was made from what is shown.
  const analysisKey = isCriticalPathEnabled
    ? getScheduleAnalysisKey([issue.id], () => issue, relationMap, getRelationLag)
    : "";
  const previousKeyRef = useRef(analysisKey);
  useEffect(() => {
    if (previousKeyRef.current === analysisKey) return;
    previousKeyRef.current = analysisKey;
    if (!analysisKey) return;
    // a failed refresh clears the analysis in the store, so nothing stale is left to show
    refreshScheduleAnalysis(projectId).catch(() => undefined);
  }, [analysisKey, projectId, refreshScheduleAnalysis]);

  const item = isCriticalPathEnabled ? getScheduleAnalysisItem(scheduleAnalysis, issue.id) : undefined;
  if (!item || item.is_fixed || item.total_float === null || isScheduleAnalysisLoading) return null;

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
