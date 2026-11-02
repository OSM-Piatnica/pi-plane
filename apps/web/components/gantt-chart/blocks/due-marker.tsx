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
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
import type { IBlockUpdateDependencyData, IGanttBlock } from "@plane/types";
import { cn, getDate, renderFormattedDate, renderFormattedPayloadDate } from "@plane/utils";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";
// local imports
import { getSidebarWidth } from "../helpers/sidebar-width";

type TTranslate = ReturnType<typeof useTranslation>["t"];

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

/** Start, Finish, Due and the finish-vs-due variance, as the one line a timeline marker tooltip shows. */
export const getTimelineDatesText = (dates: TTimelineDates, t: TTranslate): string => {
  const variance = getFinishVsDueVariance(dates.finish, dates.due);
  const parts = [
    [t("issue.dates.timeline.start"), dates.start],
    [t("issue.dates.timeline.finish"), dates.finish],
    [t("issue.dates.timeline.due"), dates.due],
  ].map(([label, value]) => `${label}: ${value ? renderFormattedDate(value) : "-"}`);
  if (variance !== undefined) {
    parts.push(
      variance === 0
        ? t("issue.dates.timeline.variance_on_due")
        : variance > 0
          ? t("issue.dates.timeline.variance_late", { days: variance })
          : t("issue.dates.timeline.variance_early", { days: Math.abs(variance) })
    );
  }
  return parts.join(" · ");
};

type Props = {
  block: IGanttBlock;
  ganttContainerRef: RefObject<HTMLDivElement | null>;
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
      const mouseX = event.clientX - containerLeft - getSidebarWidth(container) + container.scrollLeft;
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
        disabled={isMobile}
        layout="stacked"
        label={[
          t("issue.dates.timeline.due_marker"),
          getTimelineDatesText(dates, t),
          enableMove ? t("issue.dates.timeline.due_marker_hint") : "",
        ]
          .filter(Boolean)
          .join(" — ")}
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
