/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
// store
import { calendarLayerState } from "@/store/issue/helpers/calendar-layers";
// local imports
import { getIssueDateStatuses } from "../utils";

export type TCalendarLayerMarker = { label: string; className: string };

/**
 * The chip of a calendar block, distinct per layer: a deadline is a "Due" chip, a scheduled item marks its
 * finish day. `date` is the day tile (yyyy-mm-dd) the block is rendered in.
 */
export const useCalendarLayerMarker = (issue: TIssue, date?: string): TCalendarLayerMarker | null => {
  const { t } = useTranslation();
  const { getProjectStates } = useProjectState();
  const { getProjectById } = useProject();

  if (calendarLayerState.layer === "deadlines") {
    const stateGroup = getProjectStates(issue.project_id)?.find((state) => state?.id == issue.state_id)?.group;
    const isOverdue = getIssueDateStatuses(issue, stateGroup, getProjectById(issue.project_id)?.timezone).overdue;
    return {
      label: t("issue.dates.calendar.due_marker"),
      className: isOverdue ? "bg-danger-subtle text-danger-primary" : "bg-layer-2 text-secondary",
    };
  }
  if (date && issue.finish_date?.slice(0, 10) === date) {
    return { label: t("issue.dates.calendar.finish_marker"), className: "bg-accent-primary/10 text-accent-primary" };
  }
  return null;
};
