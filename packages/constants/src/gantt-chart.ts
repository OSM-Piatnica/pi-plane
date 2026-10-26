/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TIssueRelationTypes } from "@plane/types";

export const REVERSE_RELATIONS: { [key in TIssueRelationTypes]: TIssueRelationTypes } = {
  blocked_by: "blocking",
  blocking: "blocked_by",
  relates_to: "relates_to",
  duplicate: "duplicate",
  implements: "implemented_by",
  implemented_by: "implements",
  causes: "caused_by",
  caused_by: "causes",
  clones: "cloned_by",
  cloned_by: "clones",
  tests: "tested_by",
  tested_by: "tests",
  start_before: "start_after",
  start_after: "start_before",
  finish_before: "finish_after",
  finish_after: "finish_before",
};
