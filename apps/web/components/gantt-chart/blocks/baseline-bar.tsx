/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
import type { IGanttBlock, TBaselineVarianceItem } from "@plane/types";
import { cn, renderFormattedDate } from "@plane/utils";
// helpers
import {
  formatSignedDays,
  getBarVariance,
  getBaselineBarPosition,
  getBaselineDeadlineX,
  getBaselineTooltipLines,
  getBaselineVarianceItem,
  hasBaselineMoved,
} from "@/helpers/baseline.helper";
// hooks
import { useIssuesTimeLineChart, useTimeLineChartStore } from "@/hooks/use-timeline-chart";

const DEADLINE_MARKER_SIZE = 9;

type Props = {
  block: IGanttBlock;
  /** Draw the trace above the bar instead of below it: a parent has the bracket of its sub-work items below. */
  isAboveBar: boolean;
  /** Whether there is room after the bar for the number of days; a one day marker has its name there. */
  showVariance: boolean;
};

type TTraceProps = {
  item: TBaselineVarianceItem;
  baselineName: string;
  position: { left: number; width: number };
  blockLeft: number;
  isAboveBar: boolean;
};

/** The thin grey bar where the baseline has the work item, with the saved dates and both differences on hover. */
const BaselineTrace = function BaselineTrace(props: TTraceProps) {
  const { item, baselineName, position, blockLeft, isAboveBar } = props;
  const { t } = useTranslation();
  const lines = getBaselineTooltipLines(
    item,
    baselineName,
    { start: t("issue.dates.timeline.start"), finish: t("issue.dates.timeline.finish") },
    (date) => renderFormattedDate(date) ?? "",
    t
  );
  return (
    <Tooltip label={lines.join(" — ")} layout="stacked">
      <div
        className={cn(
          "pointer-events-auto absolute z-[4] h-1 rounded-full opacity-60",
          isAboveBar ? "top-px" : "bottom-px"
        )}
        style={{
          left: `${position.left - blockLeft}px`,
          width: `${position.width}px`,
          backgroundColor: "var(--txt-tertiary)",
        }}
        data-testid="gantt-baseline-bar"
      />
    </Tooltip>
  );
};

type TDeadlineProps = { date: string; baselineName: string; x: number; blockLeft: number };

/** The due date as the baseline has it: a hollow diamond, apart from the current deadline marker. */
const BaselineDeadlineMarker = function BaselineDeadlineMarker(props: TDeadlineProps) {
  const { date, baselineName, x, blockLeft } = props;
  const { t } = useTranslation();
  return (
    <Tooltip
      label={t("baseline.saved_deadline", { name: baselineName, date: renderFormattedDate(date) ?? "" })}
      layout="stacked"
    >
      <div
        className="pointer-events-auto absolute bottom-0.5 z-[6] rotate-45 border-2 bg-surface-1 opacity-80"
        style={{
          left: `${x - blockLeft - DEADLINE_MARKER_SIZE / 2}px`,
          width: `${DEADLINE_MARKER_SIZE}px`,
          height: `${DEADLINE_MARKER_SIZE}px`,
          borderColor: "var(--txt-tertiary)",
        }}
        data-testid="gantt-baseline-deadline"
      />
    </Tooltip>
  );
};

/** The working days the finish moved, after the bar: red when later, green when earlier, nothing when unchanged. */
const BaselineVarianceLabel = function BaselineVarianceLabel(props: { variance: number | null; left: number }) {
  const { variance, left } = props;
  const { t } = useTranslation();
  if (variance === null || variance === 0) return null;
  return (
    <span
      className={cn(
        "pointer-events-none absolute top-1/2 z-[4] -translate-y-1/2 pl-1.5 text-10 font-medium whitespace-nowrap",
        variance > 0 ? "text-danger-primary" : "text-success-primary"
      )}
      style={{ left: `${left}px` }}
      data-testid="gantt-baseline-variance"
    >
      {t("baseline.variance_days", { days: formatSignedDays(variance) })}
    </span>
  );
};

/**
 * The trace of the saved plan of a work item: a thin grey bar where the baseline has it (start to finish, like the
 * bar itself), drawn only when the work item has moved since, and the working days its finish moved next to the bar.
 * The tooltip has the saved dates and both differences. A due date that moved since gets a hollow marker where the
 * baseline had it; a due date is a deadline, not part of the schedule, so it has no number of days.
 */
export const GanttBaselineBar = observer(function GanttBaselineBar(props: Props) {
  const { block, isAboveBar, showVariance } = props;
  const { currentViewData, getPositionFromDateOnGantt } = useTimeLineChartStore();
  const { baseline: store } = useIssuesTimeLineChart();

  const item = store.isBaselineShown ? getBaselineVarianceItem(store.variance, block.id) : undefined;
  if (!item) return null;
  const dayWidth = currentViewData?.data.dayWidth;
  const getPosition = (date: string) => getPositionFromDateOnGantt(date, 0);
  const position = hasBaselineMoved(item) ? getBaselineBarPosition(item, getPosition, dayWidth) : undefined;
  const deadlineX = getBaselineDeadlineX(item, getPosition, dayWidth);
  // offsets relative to the work item's own bar, which positions this element
  const blockLeft = block.position?.marginLeft ?? 0;
  const baselineName = store.variance?.baseline?.name ?? "";

  return (
    <>
      {position && (
        <BaselineTrace
          item={item}
          baselineName={baselineName}
          position={position}
          blockLeft={blockLeft}
          isAboveBar={isAboveBar}
        />
      )}
      {deadlineX !== undefined && item.baseline_target_date && (
        <BaselineDeadlineMarker
          date={item.baseline_target_date}
          baselineName={baselineName}
          x={deadlineX}
          blockLeft={blockLeft}
        />
      )}
      {position && showVariance && (
        <BaselineVarianceLabel variance={getBarVariance(item)} left={block.position?.width ?? 0} />
      )}
    </>
  );
});
