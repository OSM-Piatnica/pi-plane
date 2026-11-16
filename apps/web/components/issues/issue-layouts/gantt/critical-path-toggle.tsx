/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { AlertTriangle } from "lucide-react";
// plane imports
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// helpers
import { getScheduleAnalysisNotices } from "@/helpers/schedule-analysis.helper";
// hooks
import { useIssuesTimeLineChart } from "@/hooks/use-timeline-chart";

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
  if (notices.includes("truncated"))
    lines.push(t("schedule_analysis.truncated", { count: scheduleAnalysis?.max_items ?? 0 }));
  if (notices.includes("cycles")) lines.push(t("schedule_analysis.cycles"));

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
