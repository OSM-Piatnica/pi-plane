/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import { CALENDAR_LAYERS, calendarLayerState, setCalendarLayer } from "@/store/issue/helpers/calendar-layers";

/** Switches the calendar between the Scheduled work and Deadlines layers. */
export const CalendarLayerToggle = observer(function CalendarLayerToggle() {
  const { t } = useTranslation();
  const activeLayer = calendarLayerState.layer;

  return (
    <div
      role="group"
      aria-label={t("issue.dates.calendar.layer_label")}
      className="flex items-center gap-0.5 rounded-sm bg-layer-1 p-0.5"
    >
      {CALENDAR_LAYERS.map((layer) => (
        <button
          key={layer}
          type="button"
          aria-pressed={activeLayer === layer}
          title={t(`issue.dates.calendar.${layer}_help`)}
          onClick={() => setCalendarLayer(layer)}
          className={cn("rounded-sm px-2.5 py-1 text-11 font-medium", {
            "bg-surface-1 text-primary shadow-raised-100": activeLayer === layer,
            "text-secondary hover:text-primary": activeLayer !== layer,
          })}
        >
          {t(`issue.dates.calendar.${layer}`)}
        </button>
      ))}
    </div>
  );
});
