/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export type TProjectOrderByOptions =
  | "sort_order"
  | "name"
  | "-name"
  | "created_at"
  | "-created_at"
  | "members_length"
  | "-members_length";

/** How the project list is split into groups; no value is one list. */
export type TProjectGroupByOptions = "initiative";

export type TProjectDisplayFilters = {
  my_projects?: boolean;
  archived_projects?: boolean;
  order_by?: TProjectOrderByOptions;
  /** Only while the Initiatives feature is on; a project in several initiatives shows in each of their groups. */
  group_by?: TProjectGroupByOptions | null;
};

export type TProjectAppliedDisplayFilterKeys = "my_projects" | "archived_projects";

export type TProjectFilters = {
  access?: string[] | null;
  lead?: string[] | null;
  members?: string[] | null;
  /** Group ids and the keywords `my_groups` / `none`. */
  groups?: string[] | null;
  /** Initiative ids, goal ids (the projects of the goal's initiatives) and the keyword `none`. */
  initiatives?: string[] | null;
  created_at?: string[] | null;
};

export type TProjectStoredFilters = {
  display_filters?: TProjectDisplayFilters;
  filters?: TProjectFilters;
};
