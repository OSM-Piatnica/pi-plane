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
  finish_date: string | null;
  new_start_date: string | null;
  new_finish_date: string | null;
  /** The due date (deadline); shifting never changes it. */
  target_date?: string | null;
  /** Working days by which the new finish passes the due date, when the shift makes the item later than it was. */
  deadline_overrun_days?: number | null;
  /** Working days the item was past its due date before the shift, given only beside a warning. */
  previous_deadline_overrun_days?: number | null;
};

/**
 * What the API offers with a date change (`error_code: relation_reschedule_available`): the dependents that move, and
 * the sub-work items that can follow their moved parents. A client that did not ask for sub-work items
 * (`offer_sub_items`) gets them empty.
 */
export type TRelationRescheduleOffer = {
  /** Dependents that move when the sub-work items stay where they are */
  shifts: TRelationRescheduleShift[];
  /** Sub-work items that can follow their moved parents */
  sub_items: TRelationRescheduleShift[];
  /** Dependents that move when the sub-work items follow */
  shifts_with_sub_items: TRelationRescheduleShift[];
};

/** The answer to a reschedule offer: whether to save the change at all, and whether the sub-work items follow. */
export type TRelationRescheduleAnswer = { confirmed: boolean; moveSubItems: boolean };
