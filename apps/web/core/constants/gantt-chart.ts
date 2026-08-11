/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TIssueRelationTypes } from "../../ce/types";

export const REVERSE_RELATIONS: { [key in TIssueRelationTypes]: TIssueRelationTypes } = {
  blocked_by: "blocking",
  blocking: "blocked_by",
  relates_to: "relates_to",
  duplicate: "duplicate",
  start_before: "start_after",
  start_after: "start_before",
  finish_before: "finish_after",
  finish_after: "finish_before",
};

export const GANTT_DEPENDENCY_RELATION_TYPES: TIssueRelationTypes[] = [
  "blocked_by",
  "blocking",
  "start_before",
  "start_after",
  "finish_before",
  "finish_after",
];
