/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { AlertTriangle } from "lucide-react";
// plane imports
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { EIssuesStoreType } from "@plane/types";
import { cn } from "@plane/utils";
// helpers
import {
  getScheduleAnalysisKey,
  getScheduleAnalysisNotices,
  getScheduleAnalysisScope,
} from "@/helpers/schedule-analysis.helper";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssuesTimeLineChart } from "@/hooks/use-timeline-chart";

type TLoaderProps = {
  issueIds: string[];
  storeType: EIssuesStoreType;
};

/**
 * Asks the server for the critical path while its toggle is on, and again when a date, a state, a relation or a lag
 * of a loaded work item changes: the key stands for all of those. It renders nothing. Being a component of its own, it
 * is the only one that re-renders when one of those changes, not the whole timeline.
 */
export const GanttScheduleAnalysisLoader = observer(function GanttScheduleAnalysisLoader(props: TLoaderProps) {
  const { issueIds, storeType } = props;
  const { t } = useTranslation();
  const { workspaceSlug, projectId, moduleId, cycleId } = useParams();
  const { isCriticalPathEnabled, fetchScheduleAnalysis } = useIssuesTimeLineChart();
  const {
    issue: { getIssueById },
    relation: { relationMap, getRelationLag },
  } = useIssueDetail();

  const { module: scopeModule, cycle: scopeCycle } = getScheduleAnalysisScope(storeType, {
    moduleId: moduleId?.toString(),
    cycleId: cycleId?.toString(),
  });
  const analysisKey = isCriticalPathEnabled
    ? getScheduleAnalysisKey(issueIds, getIssueById, relationMap, getRelationLag)
    : "";

  useEffect(() => {
    if (!isCriticalPathEnabled || !workspaceSlug || !projectId) return;
    const timeout = setTimeout(() => {
      fetchScheduleAnalysis(workspaceSlug.toString(), projectId.toString(), {
        module: scopeModule,
        cycle: scopeCycle,
      }).catch(() => {
        setToast({ type: "error", title: t("toast.error"), message: t("schedule_analysis.load_error") });
      });
    }, 300);
    return () => clearTimeout(timeout);
    // analysisKey stands for what the analysis depends on; t only matters when the request fails
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisKey, isCriticalPathEnabled, workspaceSlug, projectId, scopeModule, scopeCycle, fetchScheduleAnalysis]);

  return null;
});

/**
 * Switches the critical path on the timeline on or off: the work items whose delay moves the end of the project, and
 * the dependency lines between them, are highlighted. The analysis is computed by the server and only asked for while
 * this is on.
 */
export const GanttCriticalPathToggle = observer(function GanttCriticalPathToggle() {
  const { t } = useTranslation();
  const { isCriticalPathEnabled, toggleCriticalPath, scheduleAnalysis } = useIssuesTimeLineChart();

  const notices = getScheduleAnalysisNotices(scheduleAnalysis);
  const lines = [t("schedule_analysis.critical_path_tooltip")];
  // a truncated analysis highlights nothing: it only describes a cut-off part of the plan
  if (notices.includes("truncated"))
    lines.push(t("schedule_analysis.truncated", { count: scheduleAnalysis?.max_items ?? 0 }));
  if (notices.includes("cycles")) lines.push(t("schedule_analysis.cycles"));
  if (notices.includes("inverted")) lines.push(t("schedule_analysis.inverted"));

  return (
    <Tooltip label={lines.join(" ")} layout="stacked">
      <button
        type="button"
        className={cn(
          "flex items-center gap-1 rounded-md bg-layer-transparent p-1 px-2 text-11 hover:bg-layer-transparent-hover",
          { "bg-layer-transparent-selected": isCriticalPathEnabled }
        )}
        aria-pressed={isCriticalPathEnabled}
        onClick={toggleCriticalPath}
        data-testid="gantt-critical-path-toggle"
      >
        {t("schedule_analysis.critical_path")}
        {notices.length > 0 && <AlertTriangle className="size-3 shrink-0 text-warning-primary" aria-hidden />}
      </button>
    </Tooltip>
  );
});
