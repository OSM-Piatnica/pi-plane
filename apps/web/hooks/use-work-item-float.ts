/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
// hooks
import { useFreshScheduleAnalysisItem } from "@/hooks/use-fresh-schedule-analysis-item";

export type TWorkItemFloat = {
  /** The float in working days, as text. */
  label: string;
  /** No float: the work item is on the critical path. */
  isCritical: boolean;
  help: string;
};

/**
 * What the Float column or property of a work item shows, or undefined where it shows nothing: the analysis is not
 * asked for, not yet answered, stale for this work item or does not cover it (undated, truncated), or the work item
 * is completed or cancelled and has no float.
 */
export const useWorkItemFloat = (issue: TIssue): TWorkItemFloat | undefined => {
  const { t } = useTranslation();
  const item = useFreshScheduleAnalysisItem(issue);
  if (!item || item.is_fixed || item.total_float === null) return undefined;
  return {
    label: t("schedule_analysis.float_days", { count: item.total_float }),
    isCritical: item.is_critical,
    help: t("schedule_analysis.float_help"),
  };
};
