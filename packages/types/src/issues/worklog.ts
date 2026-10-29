/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Time somebody logged on a work item. */
export type TIssueWorklog = {
  id: string;
  /** Minutes. */
  duration: number;
  description: string;
  logged_by: string | null;
  issue: string;
  project: string;
  workspace: string;
  created_at: string;
  updated_at: string;
};

export type TIssueWorklogsResponse = {
  worklogs: TIssueWorklog[];
  /** Minutes. */
  total_duration: number;
};
