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
