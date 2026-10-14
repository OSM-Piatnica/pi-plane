/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TCycleOrderByOptions } from "@plane/types";

// types
export const CYCLE_STATUS: {
  i18n_label: string;
  value: "current" | "upcoming" | "completed" | "draft";
  i18n_title: string;
  color: string;
  textColor: string;
  bgColor: string;
}[] = [
  {
    i18n_label: "project_cycles.status.days_left",
    value: "current",
    i18n_title: "project_cycles.status.in_progress",
    color: "#F59E0B",
    textColor: "text-amber-500",
    bgColor: "bg-amber-50",
  },
  {
    i18n_label: "project_cycles.status.yet_to_start",
    value: "upcoming",
    i18n_title: "project_cycles.status.yet_to_start",
    color: "#3F76FF",
    textColor: "text-blue-500",
    bgColor: "bg-indigo-50",
  },
  {
    i18n_label: "project_cycles.status.completed",
    value: "completed",
    i18n_title: "project_cycles.status.completed",
    color: "#16A34A",
    textColor: "text-success-primary",
    bgColor: "bg-success-subtle",
  },
  {
    i18n_label: "project_cycles.status.draft",
    value: "draft",
    i18n_title: "project_cycles.status.draft",
    color: "#525252",
    textColor: "text-tertiary",
    bgColor: "bg-surface-2",
  },
];

export const CYCLE_ORDER_BY_OPTIONS: {
  key: TCycleOrderByOptions;
  i18n_label: string;
}[] = [
  {
    key: "status",
    i18n_label: "project_cycles.order_by.status",
  },
  {
    key: "name",
    i18n_label: "project_cycles.order_by.name",
  },
  {
    key: "start_date",
    i18n_label: "project_cycles.order_by.start_date",
  },
  {
    key: "sort_order",
    i18n_label: "project_cycles.order_by.manual",
  },
];
