/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TLogoProps } from "./common";

export type TProjectTemplateCustomPropertyType = "text" | "number" | "dropdown" | "boolean" | "date" | "member_picker";

export type TProjectTemplateDropdownSelectMode = "single" | "multi";

export type TProjectTemplateCustomProperty = {
  title: string;
  description?: string;
  is_mandatory: boolean;
  is_active: boolean;
  property_type: TProjectTemplateCustomPropertyType;
  options?: string[];
  select_mode?: TProjectTemplateDropdownSelectMode;
  default_option?: string | null;
};

export type TProjectTemplateAdditionalWorkItemType = {
  name: string;
  description?: string;
  custom_properties?: TProjectTemplateCustomProperty[];
};

/**
 * A group that becomes a member of every project created from a template. The id is workspace specific, so the file also
 * carries the path ("Parent / Child"): a template uploaded into another workspace finds its groups by path.
 */
export type TProjectTemplateGroup = {
  group?: string;
  path?: string;
  /** Member (15) or Guest (5), never Admin. */
  role: 15 | 5;
};

export type TProjectTemplatePayload = {
  name?: string;
  identifier?: string;
  description?: string;
  start_date?: string | null;
  target_date?: string | null;
  network?: 0 | 1 | 2;
  project_lead?: string | null;
  default_assignee?: string | null;
  logo_props?: TLogoProps | null;
  cover_image_url?: string | null;
  cycle_view?: boolean;
  module_view?: boolean;
  issue_views_view?: boolean;
  page_view?: boolean;
  intake_view?: boolean;
  is_time_tracking_enabled?: boolean;
  is_issue_type_enabled?: boolean;
  guest_view_all_features?: boolean;
  epic_enabled?: boolean;
  state_templates?: {
    name: string;
    group?: "backlog" | "unstarted" | "started" | "completed" | "cancelled";
    color?: string | null;
    default?: boolean;
  }[];
  label_templates?: {
    name: string;
    color?: string | null;
  }[];
  task_custom_properties?: TProjectTemplateCustomProperty[];
  epic_custom_properties?: TProjectTemplateCustomProperty[];
  additional_work_item_types?: TProjectTemplateAdditionalWorkItemType[];
  groups?: TProjectTemplateGroup[];
};

export type TProjectTemplate = {
  id: string;
  name: string;
  description: string;
  payload: TProjectTemplatePayload;
  sort_order: number;
  created_at: string;
  updated_at: string;
  /** Only in the answer to a save: groups of the saved payload that match no group of this workspace. */
  unmatched_groups?: { group: string | null; path: string }[];
};

/** What applying a template's groups to a new project did. */
export type TProjectTemplateGroupsResult = {
  applied: number;
  skipped: { group: string | null; path: string }[];
};
