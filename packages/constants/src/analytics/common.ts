/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TAnalyticsTabsBase } from "@plane/types";
import { ChartXAxisProperty, ChartYAxisMetric } from "@plane/types";

export interface IInsightField {
  key: string;
  i18nKey: string;
  i18nProps?: {
    entity?: string;
    entityPlural?: string;
    prefix?: string;
    suffix?: string;
    [key: string]: unknown;
  };
}

export const ANALYTICS_INSIGHTS_FIELDS: Record<TAnalyticsTabsBase, IInsightField[]> = {
  overview: [
    {
      key: "total_users",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.users",
      },
    },
    {
      key: "total_admins",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.admins",
      },
    },
    {
      key: "total_members",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.members",
      },
    },
    {
      key: "total_guests",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.guests",
      },
    },
    {
      key: "total_projects",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.projects",
      },
    },
    {
      key: "total_work_items",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.work_items",
      },
    },
    {
      key: "total_cycles",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.cycles",
      },
    },
    {
      key: "total_intake",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "sidebar.intake",
      },
    },
  ],
  "work-items": [
    {
      key: "total_work_items",
      i18nKey: "workspace_analytics.total",
    },
    {
      key: "started_work_items",
      i18nKey: "workspace_analytics.started_work_items",
    },
    {
      key: "backlog_work_items",
      i18nKey: "workspace_analytics.backlog_work_items",
    },
    {
      key: "un_started_work_items",
      i18nKey: "workspace_analytics.un_started_work_items",
    },
    {
      key: "completed_work_items",
      i18nKey: "workspace_analytics.completed_work_items",
    },
  ],
};

export const ANALYTICS_DURATION_FILTER_OPTIONS = [
  {
    name: "Yesterday",
    i18n_name: "app_text.analytics.yesterday",
    value: "yesterday",
  },
  {
    name: "Last 7 days",
    i18n_name: "app_text.analytics.last_7_days",
    value: "last_7_days",
  },
  {
    name: "Last 30 days",
    i18n_name: "app_text.analytics.last_30_days",
    value: "last_30_days",
  },
  {
    name: "Last 3 months",
    i18n_name: "app_text.analytics.last_3_months",
    value: "last_3_months",
  },
];

export const ANALYTICS_X_AXIS_VALUES: { value: ChartXAxisProperty; label: string; i18n_label: string }[] = [
  {
    value: ChartXAxisProperty.STATES,
    label: "State name",
    i18n_label: "app_text.analytics.state_name",
  },
  {
    value: ChartXAxisProperty.STATE_GROUPS,
    label: "State group",
    i18n_label: "common.state_group",
  },
  {
    value: ChartXAxisProperty.PRIORITY,
    label: "Priority",
    i18n_label: "common.priority",
  },
  {
    value: ChartXAxisProperty.LABELS,
    label: "Label",
    i18n_label: "common.label",
  },
  {
    value: ChartXAxisProperty.ASSIGNEES,
    label: "Assignee",
    i18n_label: "common.assignee",
  },
  {
    value: ChartXAxisProperty.ESTIMATE_POINTS,
    label: "Estimate point",
    i18n_label: "app_text.analytics.estimate_point",
  },
  {
    value: ChartXAxisProperty.CYCLES,
    label: "Cycle",
    i18n_label: "common.cycle",
  },
  {
    value: ChartXAxisProperty.MODULES,
    label: "Module",
    i18n_label: "common.module",
  },
  {
    value: ChartXAxisProperty.COMPLETED_AT,
    label: "Completed date",
    i18n_label: "app_text.analytics.completed_date",
  },
  {
    value: ChartXAxisProperty.TARGET_DATE,
    label: "Due date",
    i18n_label: "common.order_by.due_date",
  },
  {
    value: ChartXAxisProperty.START_DATE,
    label: "Start date",
    i18n_label: "common.order_by.start_date",
  },
  {
    value: ChartXAxisProperty.CREATED_AT,
    label: "Created date",
    i18n_label: "inbox_ui.created_date",
  },
];

export const ANALYTICS_Y_AXIS_VALUES: { value: ChartYAxisMetric; label: string; i18n_label: string }[] = [
  {
    value: ChartYAxisMetric.WORK_ITEM_COUNT,
    label: "Work item",
    i18n_label: "common.work_item",
  },
  {
    value: ChartYAxisMetric.ESTIMATE_POINT_COUNT,
    label: "Estimate",
    i18n_label: "common.estimate",
  },
  {
    value: ChartYAxisMetric.EPIC_WORK_ITEM_COUNT,
    label: "Epic",
    i18n_label: "common.epic",
  },
];

export const ANALYTICS_V2_DATE_KEYS = ["completed_at", "target_date", "start_date", "created_at"];
