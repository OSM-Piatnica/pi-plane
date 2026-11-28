/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueType, TIssueTypeKind } from "@plane/types";

type TKindSource = Partial<Pick<TIssueType, "kind" | "is_epic">>;

/**
 * Kinds whose work items are created and moved by the system: a person cannot switch a work item into or out
 * of them. Mirrors `SYSTEM_MANAGED_ISSUE_TYPE_KINDS` in `apps/api/plane/db/models/issue_type.py`.
 */
export const SYSTEM_MANAGED_ISSUE_TYPE_KINDS: readonly TIssueTypeKind[] = ["approval", "review"];

/**
 * The kind of a work item type. Data cached before the server sent `kind` has only the older `is_epic` flag,
 * so that flag decides when the kind is missing. No type at all counts as the standard kind.
 */
export const getIssueTypeKind = (type: TKindSource | null | undefined): TIssueTypeKind => {
  if (!type) return "standard";
  if (type.kind) return type.kind;
  return type.is_epic ? "epic" : "standard";
};

export const isSystemManagedKind = (kind: TIssueTypeKind | null | undefined): boolean =>
  !!kind && SYSTEM_MANAGED_ISSUE_TYPE_KINDS.includes(kind);

/** True for a type of a system-managed kind (approval, review). */
export const isSystemManagedType = (type: TKindSource | null | undefined): boolean =>
  isSystemManagedKind(getIssueTypeKind(type));

/**
 * True for a type of the milestone kind: a point in the schedule, so its start equals its finish (the server keeps
 * them equal) and the timeline draws a diamond at the finish date.
 */
export const isMilestoneType = (type: TKindSource | null | undefined): boolean =>
  getIssueTypeKind(type) === "milestone";

/** True for a type of the Epic kind; falls back to `is_epic` when the type carries no kind. */
export const isEpicKind = (type: TKindSource | null | undefined): boolean => getIssueTypeKind(type) === "epic";
