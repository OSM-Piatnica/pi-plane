/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { useTranslation } from "@plane/i18n";
import type { TBaselineVariance, TBaselineVarianceItem, TProjectBaseline } from "@plane/types";

type TTranslate = ReturnType<typeof useTranslation>["t"];

/**
 * Baselines are saved and compared by the server (`plane.utils.baselines`), which also counts the working days. The
 * web app decides when to ask again and where to draw the trace of the saved plan. These helpers hold that logic.
 */

type TDatedWorkItem = {
  start_date?: string | null;
  finish_date?: string | null;
  target_date?: string | null;
};

/** A string that changes whenever a date the variance depends on changes among the loaded work items. */
export const getBaselineKey = (issueIds: string[], getIssue: (issueId: string) => TDatedWorkItem | undefined): string =>
  issueIds
    .map((issueId) => {
      const issue = getIssue(issueId);
      return [issueId, issue?.start_date ?? "", issue?.finish_date ?? "", issue?.target_date ?? ""].join("|");
    })
    .join(";");

/** What the baseline says about a work item, when there is a comparison and it covers the work item. */
export const getBaselineVarianceItem = (
  variance: TBaselineVariance | undefined,
  issueId: string | undefined
): TBaselineVarianceItem | undefined => (variance && issueId ? variance.items[issueId] : undefined);

/** Whether the bar of a work item is somewhere else than the baseline has it: only then is there a trace to draw. */
export const hasBaselineMoved = (item: TBaselineVarianceItem | undefined): boolean =>
  !!item &&
  item.in_baseline &&
  (item.baseline_start_date !== item.start_date || item.baseline_finish_date !== item.finish_date);

export type TBaselineBarPosition = { left: number; width: number };

/**
 * Where the trace of the saved plan goes on the chart, in pixels from the start of the chart: from the baseline start
 * to the end of the baseline finish day. A work item that had only one of the two dates gets a trace one day wide,
 * like its marker. `getPosition` answers the left edge of a day, `dayWidth` the width of one.
 */
export const getBaselineBarPosition = (
  item: Pick<TBaselineVarianceItem, "baseline_start_date" | "baseline_finish_date"> | undefined,
  getPosition: (date: string) => number | undefined,
  dayWidth: number | undefined
): TBaselineBarPosition | undefined => {
  if (!item || !dayWidth) return undefined;
  const first = item.baseline_start_date ?? item.baseline_finish_date;
  const last = item.baseline_finish_date ?? item.baseline_start_date;
  if (!first || !last) return undefined;
  const left = getPosition(first);
  const right = getPosition(last);
  if (left === undefined || right === undefined) return undefined;
  // a baseline that ends before it starts cannot be saved, but a width is never negative
  return { left, width: Math.max(right - left, 0) + dayWidth };
};

/**
 * Where the saved due date goes on the chart (the middle of its day, in pixels from the start of the chart), when the
 * deadline has moved since the baseline was saved. The due date is a deadline, not part of the schedule, so it gets a
 * marker of its own and never a variance.
 */
export const getBaselineDeadlineX = (
  item: Pick<TBaselineVarianceItem, "in_baseline" | "baseline_target_date" | "target_date"> | undefined,
  getPosition: (date: string) => number | undefined,
  dayWidth: number | undefined
): number | undefined => {
  if (!item?.in_baseline || !item.baseline_target_date || !dayWidth) return undefined;
  if (item.baseline_target_date === item.target_date) return undefined;
  const left = getPosition(item.baseline_target_date);
  return left === undefined ? undefined : left + dayWidth / 2;
};

/** The variance shown next to a bar: of the finish, which is what moves the plan, else of the start. */
export const getBarVariance = (item: TBaselineVarianceItem | undefined): number | null => {
  if (!item?.in_baseline) return null;
  return item.finish_date_variance ?? item.start_date_variance;
};

/** A variance with its sign: "+3", "-2", "0". The minus is a real minus sign, as wide as the plus. */
export const formatSignedDays = (days: number): string => {
  if (days > 0) return `+${days}`;
  if (days < 0) return `−${Math.abs(days)}`;
  return "0";
};

/** A variance in working days, with its sign ("+3 d"), or "as planned" for none. */
export const getVarianceText = (days: number, t: TTranslate): string =>
  days === 0 ? t("baseline.on_plan") : t("baseline.variance_days", { days: formatSignedDays(days) });

/**
 * What the tooltip of a trace says: the saved dates, then how far the start and the finish moved. A date that was
 * not set then, or is not set now, has nothing to compare and is left out.
 */
export const getBaselineTooltipLines = (
  item: TBaselineVarianceItem,
  baselineName: string,
  labels: { start: string; finish: string },
  formatDate: (date: string) => string,
  t: TTranslate
): string[] => {
  const first = item.baseline_start_date ?? item.baseline_finish_date;
  const last = item.baseline_finish_date ?? item.baseline_start_date;
  const lines: string[] = [];
  if (first && last)
    lines.push(t("baseline.bar_tooltip", { name: baselineName, start: formatDate(first), end: formatDate(last) }));
  const moves: string[] = [];
  if (item.start_date_variance !== null) moves.push(`${labels.start}: ${getVarianceText(item.start_date_variance, t)}`);
  if (item.finish_date_variance !== null)
    moves.push(`${labels.finish}: ${getVarianceText(item.finish_date_variance, t)}`);
  if (moves.length > 0) lines.push(moves.join(" · "));
  return lines;
};

/** The baseline the timeline compares with: the one a person picked, else the active one of the project. */
export const getComparedBaseline = (
  baselines: TProjectBaseline[] | undefined,
  selectedBaselineId: string | undefined
): TProjectBaseline | undefined =>
  baselines?.find((baseline) => baseline.id === selectedBaselineId) ??
  baselines?.find((baseline) => baseline.is_active);

/** The name offered for a new baseline: the day it is saved, as the person reads dates. */
export const getDefaultBaselineName = (label: string, formattedDate: string): string => `${label} ${formattedDate}`;
