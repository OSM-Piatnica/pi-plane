/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// hooks
import { useIssuesTimeLineChart } from "@/hooks/use-timeline-chart";

/** Switches the dates that parents take from the work items below them on or off. */
export const GanttRollupToggle = observer(function GanttRollupToggle() {
  const { t } = useTranslation();
  const { isDateRollupEnabled, toggleDateRollup } = useIssuesTimeLineChart();

  return (
    <button
      type="button"
      className={cn("rounded-md bg-layer-transparent p-1 px-2 text-11 hover:bg-layer-transparent-hover", {
        "bg-layer-transparent-selected": isDateRollupEnabled,
      })}
      aria-pressed={isDateRollupEnabled}
      onClick={toggleDateRollup}
    >
      {t("timeline_rollup.roll_up_dates")}
    </button>
  );
});
