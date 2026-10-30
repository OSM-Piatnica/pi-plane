/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TLogoProps } from "../common";
import type { TUserPermissions } from "../enums";
import type { TStateGroups } from "../state";
import type { EStartOfTheWeek, IUser, IUserLite } from "../users";
import type { IWorkspace } from "../workspace";

export enum EUserProjectRoles {
  ADMIN = 20,
  MEMBER = 15,
  GUEST = 5,
}

export interface IPartialProject {
  id: string;
  name: string;
  identifier: string;
  sort_order: number | null;
  logo_props: TLogoProps;
  member_role?: TUserPermissions | EUserProjectRoles | null;
  archived_at: string | null;
  workspace: IWorkspace | string;
  cycle_view: boolean;
  issue_views_view: boolean;
  module_view: boolean;
  page_view: boolean;
  inbox_view: boolean;
  guest_view_all_features?: boolean;
  is_issue_type_enabled?: boolean;
  is_workflow_enabled?: boolean;
  is_parent_completion_rule_enabled?: boolean;
  is_blocked_status_rule_enabled?: boolean;
  is_assignee_edit_rule_enabled?: boolean;
  is_relation_schedule_enabled?: boolean;
  is_relation_traceability_enabled?: boolean;
  is_relation_relates_to_enabled?: boolean;
  is_relation_duplicate_enabled?: boolean;
  is_time_tracking_enabled?: boolean;
  project_lead?: IUserLite | string | null;
  network?: number;
  /** Whether the signed-in user has an open request to join this Private project (gallery list only). */
  has_pending_access_request?: boolean;
  // Timestamps
  created_at?: Date;
  updated_at?: Date;
  // actor
  created_by?: string;
  updated_by?: string;
  intake_count?: number;
}

export interface IProject extends IPartialProject {
  archive_in?: number;
  close_in?: number;
  // only for uploading the cover image
  cover_image_asset?: null;
  cover_image?: string;
  // only for rendering the cover image
  readonly cover_image_url?: string;
  default_assignee?: IUser | string | null;
  default_state?: string | null;
  description?: string;
  estimate?: string | null;
  anchor?: string | null;
  is_favorite?: boolean;
  members?: string[];
  /** Groups the project has as project groups, incl. the ones above them, restricted to the ones the requester may filter by. */
  group_ids?: string[];
  /** Whether the project has any project group at all. */
  has_group?: boolean;
  /** Whether the project has a project group among the requester's groups. */
  in_my_groups?: boolean;
  timezone?: string;
  start_of_the_week?: EStartOfTheWeek;
  /** Days that count as non-working time in this project, 0 = Sunday ... 6 = Saturday. */
  weekend_days?: number[];
  start_date?: string | null;
  target_date?: string | null;
  next_work_item_sequence?: number;
}

export type TProjectAnalyticsCountParams = {
  project_ids?: string;
  fields?: string;
};

export type TProjectAnalyticsCount = Pick<IProject, "id"> & {
  total_issues?: number;
  completed_issues?: number;
  total_cycles?: number;
  total_members?: number;
  total_modules?: number;
};

export interface IProjectLite {
  id: string;
  name: string;
  identifier: string;
  logo_props: TLogoProps;
}

export interface IProjectMap {
  [id: string]: IProject;
}

export interface IProjectMemberLite {
  id: string;
  member__avatar_url: string;
  member__display_name: string;
  member_id: string;
}

export type TProjectMembership = {
  member: string;
  role: TUserPermissions | EUserProjectRoles;
  /** True when the person is a member of the project only through a group. */
  via_group?: boolean;
  /** The best role the project's groups give the person (null: no group gives one). */
  group_role?: EUserProjectRoles | null;
  /** The person's own role while a group raised it above that (null: no group raised it). */
  direct_role?: EUserProjectRoles | null;
} & (
  | {
      id: string;
      original_role: EUserProjectRoles;
      created_at: string;
    }
  | {
      id: null;
      original_role: null;
      created_at: null;
    }
);

export interface IProjectBulkAddFormData {
  members: { role: TUserPermissions | EUserProjectRoles; member_id: string }[];
}

export type IProjectMemberNavigationPreferences = {
  default_tab: string;
  hide_in_more_menu: string[];
};

export type IProjectMemberPreferencesUpdate = {
  navigation: IProjectMemberNavigationPreferences;
};

export type IProjectMemberPreferencesResponse = {
  preferences: {
    navigation: IProjectMemberNavigationPreferences;
  };
};

export type IProjectMemberPreferencesFullResponse = IProjectMemberPreferencesResponse & {
  project_id: string;
  member_id: string;
  workspace_id: string;
};

export interface IGithubRepository {
  id: string;
  full_name: string;
  html_url: string;
  url: string;
}

export interface GithubRepositoriesResponse {
  repositories: IGithubRepository[];
  total_count: number;
}

export type TProjectIssuesSearchParams = {
  search: string;
  parent?: boolean;
  issue_relation?: boolean;
  cycle?: boolean;
  module?: string;
  sub_issue?: boolean;
  issue_id?: string;
  workspace_search: boolean;
  target_date?: string;
  epic?: boolean;
};

export interface ISearchIssueResponse {
  id: string;
  name: string;
  project_id: string;
  project__identifier: string;
  project__name: string;
  sequence_id: number;
  start_date: string | null;
  state__color: string;
  state__group: TStateGroups;
  state__name: string;
  workspace__slug: string;
  type_id: string;
}

export type TPartialProject = IPartialProject;

export type TProject = TPartialProject & IProject;

/** What to carry into a duplicated project; states and work item types are always copied. */
export type TProjectDuplicateInclude = {
  labels?: boolean;
  estimates?: boolean;
  intake?: boolean;
  members?: boolean;
  cycles?: boolean;
  modules?: boolean;
  views?: boolean;
  /** Copied in the background after the project exists; see `work_item_properties`. */
  work_items?: boolean;
};

export type TProjectDuplicatePayload = {
  name?: string;
  identifier?: string;
  network?: number;
  include?: TProjectDuplicateInclude;
  /** Which parts of the work items to carry; only used with `include.work_items`. Absent means all. */
  work_item_properties?: string[];
};

export type TProjectCopySummary = {
  source_project_id: string;
  counts: Record<string, number>;
  /** Things the copy did not carry over, e.g. `webhooks:not-copied` or `views:private`. */
  skipped: string[];
  /** Present when work items were asked for: the background copy that brings them. */
  work_items?: { job_id: string; status: TProjectCopyJobStatus; total: number; copied: number };
};

export type TProjectCopyJobStatus =
  | "queued"
  | "processing"
  | "completed"
  | "completed_with_errors"
  | "failed"
  | "cancelled";

/** The background copy of a duplicated project's work items. */
export type TProjectCopyJob = {
  id: string;
  status: TProjectCopyJobStatus;
  stage: string;
  total: number;
  copied: number;
  counts: Record<string, number>;
  skipped: string[];
  errors: { error: string }[];
  reason: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type TProjectAccessRequestStatus = "pending" | "approved" | "rejected";

/** A request to join a Private project; `status` is null when the user has not asked. */
export type TProjectAccessRequest = {
  id: string;
  project: string;
  requester: string;
  requester_detail: IUserLite;
  status: TProjectAccessRequestStatus;
  message: string;
  decided_at: string | null;
  created_at: string;
};
