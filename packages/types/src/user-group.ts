/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IUserLite } from "./users";

/** Where a group comes from: made in the workspace, or mirrored from the identity provider a person signed in with. */
export type TUserGroupSource = "local" | "entra" | "google" | "oidc";

/** A role inside one group, and the groups nested below it. */
export enum EUserGroupRole {
  ADMIN = 20,
  MEMBER = 15,
}

export type TUserGroup = {
  id: string;
  name: string;
  description: string;
  parent: string | null;
  source: TUserGroupSource;
  external_id: string | null;
  is_external: boolean;
  /** Direct members only. */
  member_count: number;
  /** What the requester may do with this group. */
  can_manage: boolean;
  can_delete: boolean;
  created_at: string;
};

export type TUserGroupFormData = {
  name: string;
  description?: string;
  parent?: string | null;
};

export type TUserGroupMember = {
  id: string;
  user: IUserLite;
  group: string;
  group_name: string;
  role: EUserGroupRole;
  /** Put in by the identity provider's sync, so it cannot be changed here. */
  managed_externally: boolean;
  created_at: string;
};

/** The roles a group can have in a project. Project admins stay named people. */
export enum EProjectGroupRole {
  MEMBER = 15,
  GUEST = 5,
}

/** A group that is a member of a project. */
export type TProjectGroup = {
  id: string;
  group: string;
  group_name: string;
  group_source: TUserGroupSource;
  role: EProjectGroupRole;
  /** People who belong to the project through this group (subgroups included). */
  member_count: number;
};

export type TProjectGroupFormData = {
  group: string;
  role: EProjectGroupRole;
};

/** A group a work item of the project can be assigned to. */
export type TAssignableGroup = {
  id: string;
  name: string;
  source: TUserGroupSource;
  parent_id: string | null;
};

/** A group the requester may filter by (work items, modules, cycles), see the filterable groups endpoint. */
export type TFilterableUserGroup = {
  id: string;
  name: string;
  source: TUserGroupSource;
  parent_id: string | null;
  /** The requester belongs to this group (it is one of the groups "my groups" stands for). */
  is_member: boolean;
};

/** One row of the project members CSV: a person (email) or a group (name or "Parent / Child" path), and a role. */
export type TProjectMemberImportRow = {
  /** The line of the CSV file, to point at the row in the report. */
  row: number;
  email?: string;
  group?: string;
  role: string;
  /** The Source column of a file written by the members export; "person (via group)" rows are not imported. */
  source?: string;
};

export type TProjectMemberImportSkipped = {
  row: number;
  type: "person" | "group";
  value: string;
  /** Stable reason code, translated by the web; `reason` is the English fallback. */
  code: string;
  reason: string;
};

export type TProjectMemberImportSummary = {
  people: { added: number; reactivated: number; already_members: number; skipped: number };
  groups: { added: number; updated: number; skipped: number };
  skipped: TProjectMemberImportSkipped[];
};

export type TProjectMemberExportFormat = "csv" | "xlsx" | "json";

export type TProjectMemberExportParams = {
  format: TProjectMemberExportFormat;
  /** Also write the people who belong to the project only through a group. */
  include_via_group: 0 | 1;
  delimiter?: "," | ";";
};
