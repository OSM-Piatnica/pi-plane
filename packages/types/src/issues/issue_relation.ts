/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TIssue } from "./issue";

export type TIssueRelationTypes =
  | "blocking"
  | "blocked_by"
  | "duplicate"
  | "relates_to"
  | "start_before"
  | "start_after"
  | "finish_before"
  | "finish_after"
  | "implements"
  | "implemented_by"
  | "causes"
  | "caused_by"
  | "clones"
  | "cloned_by"
  | "tests"
  | "tested_by"
  | "start_before_finish"
  | "finish_after_start";

export type TIssueRelation = Record<TIssueRelationTypes, TIssue[]>;

export type TIssueRelationMap = {
  [issue_id: string]: Record<TIssueRelationTypes, string[]>;
};

export type TIssueRelationIdMap = Record<TIssueRelationTypes, string[]>;

/** A work item the API offers to move along with a date change that would otherwise break a dependency. */
export type TRelationRescheduleShift = {
  id: string;
  project_id: string;
  sequence_id: number;
  ref: string;
  name: string;
  start_date: string | null;
  target_date: string | null;
  new_start_date: string | null;
  new_target_date: string | null;
};
