/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * The two values, next to group ids, that the group filters of work items, modules and cycles accept.
 * The API understands the same keywords.
 */
export const GROUP_FILTER_KEYWORDS = {
  /** Everything that belongs to a group the person is in. */
  MY_GROUPS: "my_groups",
  /** Everything that has no group. */
  NONE: "none",
} as const;

export type TGroupFilterKeyword = (typeof GROUP_FILTER_KEYWORDS)[keyof typeof GROUP_FILTER_KEYWORDS];
