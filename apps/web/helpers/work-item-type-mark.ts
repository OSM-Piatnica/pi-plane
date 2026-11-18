/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from Hangar (szymczag/hangar, AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import type { TIssueType, TLogoProps } from "@plane/types";

/** Whether a logo names something to draw: an emoji, or an icon. */
export const hasLogo = (logo: Partial<TLogoProps> | null | undefined): boolean =>
  (logo?.in_use === "emoji" && !!logo.emoji?.value) || (logo?.in_use === "icon" && !!logo.icon?.name);

/**
 * What marks a work item type next to the identifier of its work items: the logo an admin picked, else a built-in
 * mark for the Epic type, else a general one.
 */
export const getWorkItemTypeMarkKind = (
  issueType: Pick<TIssueType, "logo_props" | "is_epic">
): "logo" | "epic" | "default" => {
  if (hasLogo(issueType.logo_props)) return "logo";
  return issueType.is_epic ? "epic" : "default";
};
