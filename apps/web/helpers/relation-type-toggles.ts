/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IProject, TIssueRelationTypes } from "@plane/types";

export type TRelationToggleFlag = keyof Pick<
  IProject,
  | "is_relation_schedule_enabled"
  | "is_relation_traceability_enabled"
  | "is_relation_relates_to_enabled"
  | "is_relation_duplicate_enabled"
>;

// Mirrors plane/utils/relation_type_toggles.py. Blocking is not listed: it is always available.
export const RELATION_TOGGLE_GROUPS: Record<TRelationToggleFlag, TIssueRelationTypes[]> = {
  is_relation_schedule_enabled: [
    "start_before",
    "start_after",
    "finish_before",
    "finish_after",
    "start_before_finish",
    "finish_after_start",
  ],
  is_relation_traceability_enabled: [
    "implemented_by",
    "implements",
    "caused_by",
    "causes",
    "cloned_by",
    "clones",
    "tested_by",
    "tests",
  ],
  is_relation_relates_to_enabled: ["relates_to"],
  is_relation_duplicate_enabled: ["duplicate"],
};

export const RELATION_TOGGLE_DEFAULTS: Record<TRelationToggleFlag, boolean> = {
  is_relation_schedule_enabled: false,
  is_relation_traceability_enabled: false,
  is_relation_relates_to_enabled: true,
  is_relation_duplicate_enabled: true,
};

const FLAG_BY_TYPE = new Map<TIssueRelationTypes, TRelationToggleFlag>(
  (Object.keys(RELATION_TOGGLE_GROUPS) as TRelationToggleFlag[]).flatMap((flag) =>
    RELATION_TOGGLE_GROUPS[flag].map((type) => [type, flag] as const)
  )
);

/** Whether the project lets people add relations of this type; a project without the flags uses the defaults. */
export const isRelationTypeEnabled = (
  project: Partial<Pick<IProject, TRelationToggleFlag>> | undefined,
  relationType: TIssueRelationTypes
): boolean => {
  const flag = FLAG_BY_TYPE.get(relationType);
  if (!flag) return true;
  return project?.[flag] ?? RELATION_TOGGLE_DEFAULTS[flag];
};
