/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import type { TProjectAppliedDisplayFilterKeys, TProjectOrderByOptions } from "@plane/types";
// local imports

export type TNetworkChoiceIconKey = "Shield" | "Lock" | "Globe2";

export type TNetworkChoice = {
  key: 0 | 1 | 2;
  labelKey: string;
  i18n_label: string;
  description: string;
  iconKey: TNetworkChoiceIconKey;
};

export const NETWORK_CHOICES: TNetworkChoice[] = [
  {
    key: 0,
    labelKey: "Secret",
    i18n_label: "workspace_projects.network.secret.title",
    description: "workspace_projects.network.secret.description", //"Invisible to everyone who is not a member",
    iconKey: "Shield",
  },
  {
    key: 1,
    labelKey: "Private",
    i18n_label: "workspace_projects.network.private.title",
    description: "workspace_projects.network.private.description", //"Visible to the workspace, but locked: request access or be invited",
    iconKey: "Lock",
  },
  {
    key: 2,
    labelKey: "Public",
    i18n_label: "workspace_projects.network.public.title",
    description: "workspace_projects.network.public.description", //"Anyone in the workspace except Guests can join",
    iconKey: "Globe2",
  },
];

export const GROUP_CHOICES = {
  backlog: {
    key: "backlog",
    i18n_label: "workspace_projects.state.backlog",
  },
  unstarted: {
    key: "unstarted",
    i18n_label: "workspace_projects.state.unstarted",
  },
  started: {
    key: "started",
    i18n_label: "workspace_projects.state.started",
  },
  completed: {
    key: "completed",
    i18n_label: "workspace_projects.state.completed",
  },
  cancelled: {
    key: "cancelled",
    i18n_label: "workspace_projects.state.cancelled",
  },
};

export const PROJECT_AUTOMATION_MONTHS = [
  { i18n_label: "workspace_projects.common.months_count", value: 1 },
  { i18n_label: "workspace_projects.common.months_count", value: 3 },
  { i18n_label: "workspace_projects.common.months_count", value: 6 },
  { i18n_label: "workspace_projects.common.months_count", value: 9 },
  { i18n_label: "workspace_projects.common.months_count", value: 12 },
];

export const PROJECT_ORDER_BY_OPTIONS: {
  key: TProjectOrderByOptions;
  i18n_label: string;
}[] = [
  {
    key: "sort_order",
    i18n_label: "workspace_projects.sort.manual",
  },
  {
    key: "name",
    i18n_label: "workspace_projects.sort.name",
  },
  {
    key: "created_at",
    i18n_label: "workspace_projects.sort.created_at",
  },
  {
    key: "members_length",
    i18n_label: "workspace_projects.sort.members_length",
  },
];

export const PROJECT_DISPLAY_FILTER_OPTIONS: {
  key: TProjectAppliedDisplayFilterKeys;
  i18n_label: string;
}[] = [
  {
    key: "my_projects",
    i18n_label: "workspace_projects.scope.my_projects",
  },
  {
    key: "archived_projects",
    i18n_label: "workspace_projects.scope.archived_projects",
  },
];

export const PROJECT_ERROR_MESSAGES = {
  permissionError: {
    i18n_title: "workspace_projects.error.permission",
    i18n_message: undefined,
  },
  cycleDeleteError: {
    i18n_title: "error",
    i18n_message: "workspace_projects.error.cycle_delete",
  },
  moduleDeleteError: {
    i18n_title: "error",
    i18n_message: "workspace_projects.error.module_delete",
  },
  issueDeleteError: {
    i18n_title: "error",
    i18n_message: "workspace_projects.error.issue_delete",
  },
};

/** Longest project identifier (the "PROJ" in PROJ-12) the project forms accept; the API column (`Project.identifier`) holds 12. */
export const PROJECT_IDENTIFIER_MAX_LENGTH = 12;

export enum EProjectFeatureKey {
  WORK_ITEMS = "work_items",
  CYCLES = "cycles",
  MODULES = "modules",
  VIEWS = "views",
  PAGES = "pages",
  INTAKE = "intake",
}

/**
 * What a duplicated project can carry of its work items, in groups for the duplicate form. Mirrors
 * `WORK_ITEM_PROPERTY_GROUPS` of the API (a web test keeps the two in step).
 */
export const PROJECT_COPY_WORK_ITEM_PROPERTY_GROUPS = {
  content: ["dates", "custom_properties", "description_images"],
  people: ["assignees"],
  organization: ["labels", "cycles", "modules"],
  hierarchy: ["parents", "relations", "links"],
} as const;

/** The most work items a project copy takes along; mirrors `MAX_WORK_ITEMS` of the API. */
export const PROJECT_COPY_MAX_WORK_ITEMS = 20_000;
