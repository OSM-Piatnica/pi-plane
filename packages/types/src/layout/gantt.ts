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
