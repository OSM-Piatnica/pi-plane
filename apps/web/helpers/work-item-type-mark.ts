/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from Hangar (szymczag/hangar, AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import type { TIssueType, TIssueTypeKind, TLogoProps } from "@plane/types";
import { getIssueTypeKind } from "@plane/utils";

/** Whether a logo names something to draw: an emoji, or an icon. */
export const hasLogo = (logo: Partial<TLogoProps> | null | undefined): boolean =>
  (logo?.in_use === "emoji" && !!logo.emoji?.value) || (logo?.in_use === "icon" && !!logo.icon?.name);

export type TWorkItemTypeMarkKind = "logo" | Exclude<TIssueTypeKind, "standard"> | "default";

/**
 * What marks a work item type next to the identifier of its work items: the logo an admin picked, else a built-in
 * mark for the kind of the type (epic, milestone, approval, review), else a general one. The kind falls back to
 * `is_epic` for data cached before the server sent kinds.
 */
export const getWorkItemTypeMarkKind = (
  issueType: Pick<TIssueType, "logo_props"> & Partial<Pick<TIssueType, "kind" | "is_epic">>
): TWorkItemTypeMarkKind => {
  if (hasLogo(issueType.logo_props)) return "logo";
  const kind = getIssueTypeKind(issueType);
  return kind === "standard" ? "default" : kind;
};
