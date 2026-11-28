/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * The roles a department can have on a work item, by their neutral names. The letters people see
 * (R / A / C / I in English, O / Z / K / I in Polish) come from the translations.
 */
export const RACI_ROLES = ["responsible", "approver", "consulted", "informed"] as const;
export type TRaciRole = (typeof RACI_ROLES)[number];

/** The role of one department (a user group of kind "department") on a work item. */
export type TIssueRaciEntry = {
  group_id: string;
  role: TRaciRole;
};

/** What the RACI endpoint of a work item answers. */
export type TIssueRaci = {
  raci: TIssueRaciEntry[];
  /** Whether the requester may change the roles: a project admin or the project lead. */
  can_edit: boolean;
};

/**
 * The events on a work item the RACI notification matrix of a workspace covers, in the order they are listed.
 * `approval_requested` and `approval_decided` belong to acceptance and are sent once it exists.
 */
export const RACI_NOTIFICATION_EVENTS = [
  "new_version",
  "comment",
  "approval_requested",
  "approval_decided",
  "completed",
  "state_or_due_date",
] as const;
export type TRaciNotificationEvent = (typeof RACI_NOTIFICATION_EVENTS)[number];

/** Which roles hear about which event. */
export type TRaciNotificationMatrix = Record<TRaciNotificationEvent, TRaciRole[]>;

/** What the RACI notification settings of a workspace answer. */
export type TRaciNotificationSettings = {
  events: TRaciNotificationEvent[];
  matrix: TRaciNotificationMatrix;
  defaults: TRaciNotificationMatrix;
};

/** "Who will be notified" of one event on a work item: the departments whose role the matrix ticks, and their people. */
export type TRaciNotificationPreviewEvent = {
  event: TRaciNotificationEvent;
  roles: TRaciRole[];
  departments: { group_id: string; role: TRaciRole; member_count: number }[];
  member_ids: string[];
};

export type TRaciNotificationPreview = {
  events: TRaciNotificationPreviewEvent[];
};

/** The warnings about work items in the RACI warnings of a project, in the order they are listed. */
export const RACI_ITEM_WARNINGS = [
  "no_responsible",
  "milestone_without_approver",
  "no_predecessor",
  "no_successor",
] as const;
export type TRaciItemWarning = (typeof RACI_ITEM_WARNINGS)[number];

/** Why a department with a role tells nobody in the project. */
export type TRaciDepartmentWarningReason = "inactive" | "no_members" | "no_project_members";

export type TRaciDepartmentWarning = {
  group_id: string;
  is_active: boolean;
  member_count: number;
  project_member_count: number;
  reason: TRaciDepartmentWarningReason;
};

/** The RACI warnings of a project. Each list names at most `max_listed` work items; `counts` are complete. */
export type TRaciProjectWarnings = {
  counts: Record<TRaciItemWarning | "department_without_members", number>;
  items: Record<TRaciItemWarning, { id: string; name: string; sequence_id: number }[]>;
  departments: TRaciDepartmentWarning[];
  max_listed: number;
};
