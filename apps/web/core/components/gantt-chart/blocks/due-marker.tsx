/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { RefObject } from "react";
import { useState } from "react";
import { addDays, differenceInCalendarDays } from "date-fns";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
import type { IBlockUpdateDependencyData, IGanttBlock } from "@plane/types";
import { cn, getDate, renderFormattedDate, renderFormattedPayloadDate } from "@plane/utils";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";
// local imports
import { SIDEBAR_WIDTH } from "../constants";

type TTimelineDates = {
  start?: string | null;
  finish?: string | null;
  due?: string | null;
};

/** Signed number of days the finish falls after the due date (positive means late), when both exist. */
export const getFinishVsDueVariance = (finish?: string | null, due?: string | null): number | undefined => {
  const finishDate = getDate(finish);
  const dueDate = getDate(due);
  if (!finishDate || !dueDate) return undefined;
  return differenceInCalendarDays(finishDate, dueDate);
};

/** Start, Finish, Due and the finish-vs-due variance. Shared by every timeline marker tooltip. */
export const TimelineDatesSummary = observer(function TimelineDatesSummary(props: { dates: TTimelineDates }) {
  const { dates } = props;
  const { t } = useTranslation();
  const variance = getFinishVsDueVariance(dates.finish, dates.due);
  const rows: [string, string | null | undefined][] = [
    [t("issue.dates.timeline.start"), dates.start],
    [t("issue.dates.timeline.finish"), dates.finish],
    [t("issue.dates.timeline.due"), dates.due],
  ];

  return (
    <div className="flex flex-col gap-0.5 text-11">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-3">
          <span className="text-tertiary">{label}</span>
          <span className="font-medium">{value ? renderFormattedDate(value) : "-"}</span>
        </div>
      ))}
      {variance !== undefined && (
        <div className="mt-0.5 border-t border-subtle pt-0.5">
          {variance === 0
            ? t("issue.dates.timeline.variance_on_due")
            : variance > 0
              ? t("issue.dates.timeline.variance_late", { days: variance })
              : t("issue.dates.timeline.variance_early", { days: Math.abs(variance) })}
        </div>
      )}
    </div>
  );
});

type Props = {
  block: IGanttBlock;
  ganttContainerRef: RefObject<HTMLDivElement>;
  /** Left offset (px) the marker's positioning parent has from the start of the chart. */
  parentOffset: number;
  enableMove: boolean;
  updateBlockDates?: (updates: IBlockUpdateDependencyData[]) => Promise<void>;
};

const MARKER_SIZE = 12;

/**
 * Deadline marker of a work item. It is independent of the bar: dragging it (or using the arrow keys)
 * changes only the due date, and the bar and any dependent work item stay where they are.
 */
export const GanttDueMarker = observer(function GanttDueMarker(props: Props) {
  const { block, ganttContainerRef, parentOffset, enableMove, updateBlockDates } = props;
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  const { currentViewData, getPositionFromDateOnGantt, getDateFromPositionOnGantt } = useTimeLineChartStore();
  // x (px from chart start) of the day cell the marker is being dragged over
  const [dragX, setDragX] = useState<number | undefined>();

  const dueDate = getDate(block.due_date);
  if (!dueDate || !currentViewData) return null;

  const dayWidth = currentViewData.data.dayWidth;
  const dueX = getPositionFromDateOnGantt(dueDate, 0) ?? 0;
  const cellX = dragX ?? dueX;
  const left = cellX + dayWidth / 2 - parentOffset - MARKER_SIZE / 2;
  const shownDate = dragX !== undefined ? getDateFromPositionOnGantt(dragX, 0) : dueDate;

  const commit = (date: Date | undefined) => {
    const payloadDate = renderFormattedPayloadDate(date);
    if (!payloadDate || payloadDate === renderFormattedPayloadDate(dueDate)) return;
    updateBlockDates?.([{ id: block.id, due_date: payloadDate, meta: block.meta }]);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLButtonElement>) => {
    const container = ganttContainerRef.current;
    if (!enableMove || e.button !== 0 || !container) return;
    e.preventDefault();
    e.stopPropagation();
    const containerLeft = container.getBoundingClientRect().left;
    let moved = false;
    let lastX = dueX;

    const handleMouseMove = (event: MouseEvent) => {
      const mouseX = event.clientX - containerLeft - SIDEBAR_WIDTH + container.scrollLeft;
      lastX = Math.floor(mouseX / dayWidth) * dayWidth;
      moved = moved || lastX !== dueX;
      setDragX(lastX);
    };
    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      setDragX(undefined);
      if (moved) commit(getDateFromPositionOnGantt(lastX, 0));
    };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (!enableMove || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    e.preventDefault();
    commit(addDays(dueDate, e.key === "ArrowLeft" ? -1 : 1));
  };

  const issue = block.data ?? {};
  const dates: TTimelineDates = {
    start: issue.start_date,
    finish: issue.finish_date,
    due: shownDate ? renderFormattedPayloadDate(shownDate) : block.due_date,
  };

  return (
    <div className="pointer-events-auto absolute bottom-0 z-[7]" style={{ left: `${left}px` }}>
      <Tooltip
        isMobile={isMobile}
        tooltipContent={
          <div className="flex flex-col gap-1">
            <div className="font-medium">{t("issue.dates.timeline.due_marker")}</div>
            <TimelineDatesSummary dates={dates} />
            {enableMove && <div className="text-tertiary">{t("issue.dates.timeline.due_marker_hint")}</div>}
          </div>
        }
      >
        <button
          type="button"
          aria-label={`${t("issue.dates.timeline.due_marker")}: ${shownDate ? renderFormattedDate(shownDate) : ""}`}
          className={cn(
            "border-surface-1 block rotate-45 border bg-danger-primary transition-transform hover:scale-125 focus-visible:scale-125 focus-visible:outline-2",
            enableMove ? "cursor-ew-resize" : "cursor-default"
          )}
          style={{ width: `${MARKER_SIZE}px`, height: `${MARKER_SIZE}px` }}
          onMouseDown={handleMouseDown}
          onKeyDown={handleKeyDown}
          onClick={(e) => e.stopPropagation()}
        />
      </Tooltip>
    </div>
  );
});
