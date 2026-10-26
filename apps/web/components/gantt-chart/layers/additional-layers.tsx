/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { FC } from "react";
import { observer } from "mobx-react";
// hooks
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";
import { useWeekendDays } from "@/hooks/use-weekend-days";
// local imports
import { getOffDayPositions } from "../helpers/off-day-positions";

type Props = {
  itemsContainerWidth: number;
  blockCount: number;
};

// A day is 5px wide in the quarter view, too narrow to tell shaded days apart
const VIEWS_WITH_OFF_DAYS = new Set(["week", "month"]);

/** Shades the project's non-working days across the whole height of the timeline. */
export const GanttAdditionalLayers: FC<Props> = observer(function GanttAdditionalLayers() {
  const { currentView, currentViewData } = useTimeLineChartStore();
  const weekendDays = useWeekendDays();

  if (!currentView || !currentViewData || !VIEWS_WITH_OFF_DAYS.has(currentView) || weekendDays.length === 0)
    return null;

  const { startDate, endDate, dayWidth } = currentViewData.data;
  const positions = getOffDayPositions(startDate, endDate, dayWidth, weekendDays);

  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true" data-testid="gantt-off-days">
      {positions.map((left) => (
        <div key={left} className="absolute inset-y-0 bg-layer-1" style={{ left, width: dayWidth }} />
      ))}
    </div>
  );
});
