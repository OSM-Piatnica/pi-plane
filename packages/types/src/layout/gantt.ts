/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export enum EGanttBlockType {
  EPIC = "epic",
  PROJECT = "project",
  ISSUE = "issue",
}
export interface IGanttBlock {
  data: any;
  id: string;
  name: string;
  position?: {
    marginLeft: number;
    width: number;
  };
  sort_order: number | undefined;
  start_date: string | undefined;
  /** Bar end. For work items this is the finish date, for modules and cycles their end date. */
  target_date: string | undefined;
  /** Work items only: the due date (deadline), rendered as a separate marker. Never part of the bar. */
  due_date?: string;
  meta?: Record<string, any>;
  /** Dates of the work items below this block, set when the chart rolls dates up. */
  rollup?: TGanttBlockRollup;
}

/**
 * The date span of the work items below a parent (any depth), as the server computes it: earliest start to latest
 * end. Either date is null when no descendant has one.
 */
export type TGanttDateRollup = {
  start_date: string | null;
  target_date: string | null;
  children_count: number;
  descendants_count: number;
};

export type TGanttBlockRollup = TGanttDateRollup & {
  /** Where the children's span sits on the chart; undefined when no child is dated. */
  position?: {
    marginLeft: number;
    width: number;
  };
  /**
   * The block has no own start (or end) date, so its bar takes that side from the children. Such a bar is drawn
   * hatched and cannot be dragged.
   */
  is_start_inferred: boolean;
  is_target_inferred: boolean;
};

/** Critical path analysis of one work item, as the server computes it. Dates are ISO "YYYY-MM-DD" strings. */
export type TScheduleAnalysisItem = {
  earliest_start: string;
  earliest_finish: string;
  latest_start: string;
  latest_finish: string;
  /** Working days the work item can slip without moving the end of the project; null for a fixed work item. */
  total_float: number | null;
  is_critical: boolean;
  /** Completed or cancelled: the analysis leaves its dates alone. */
  is_fixed: boolean;
  /** The latest finish that still lets the work items depending on this one meet their due dates. */
  needed_by: string | null;
};

/** The answer of the schedule analysis endpoint of a project (optionally of one module or cycle). */
export type TScheduleAnalysis = {
  project_start: string | null;
  project_end: string | null;
  items: Record<string, TScheduleAnalysisItem>;
  critical_ids: string[];
  /** Work items that depend on each other in a circle; the relations inside a circle are left out. */
  cycles: string[][];
  undated_count: number;
  undated_linked_ids: string[];
  weekend_days: number[];
  analysed_count: number;
  max_items: number;
  /** More dated work items than `max_items`: only the first ones were analysed. */
  truncated: boolean;
};

export type TScheduleAnalysisScope = { module?: string; cycle?: string };

export interface IBlockUpdateData {
  sort_order?: {
    destinationIndex: number;
    newSortOrder: number;
    sourceIndex: number;
  };
  start_date?: string;
  target_date?: string;
  meta?: Record<string, any>;
}

export interface IBlockUpdateDependencyData {
  id: string;
  start_date?: string;
  /** Bar end (work item finish date, module or cycle end date). */
  target_date?: string;
  /** Work items only: a due date change coming from the deadline marker. Never moves the bar. */
  due_date?: string;
  meta?: Record<string, any>;
}

export type TGanttViews = "week" | "month" | "quarter";

// chart render types
export interface WeekMonthDataType {
  key: number;
  shortTitle: string;
  title: string;
  abbreviation: string;
}

export interface ChartDataType {
  key: string;
  i18n_title: string;
  data: ChartDataTypeData;
}

export interface ChartDataTypeData {
  startDate: Date;
  currentDate: Date;
  endDate: Date;
  approxFilterRange: number;
  dayWidth: number;
}
