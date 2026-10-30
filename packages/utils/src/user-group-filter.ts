/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { GROUP_FILTER_KEYWORDS } from "@plane/constants";
import type { TFilterableUserGroup } from "@plane/types";

/** Separator of the names of a group and the groups above it in a label. */
const PATH_SEPARATOR = " / ";

export type TGroupFilterOption = {
  /** A group id or one of the GROUP_FILTER_KEYWORDS. */
  value: string;
  label: string;
  isKeyword: boolean;
};

export type TGroupFilterTranslate = (key: string) => string;

const KEYWORD_VALUES = new Set<string>(Object.values(GROUP_FILTER_KEYWORDS));

/** Whether the value is one of the keywords, not a group id. */
export const isGroupFilterKeyword = (value: string): boolean => KEYWORD_VALUES.has(value);

/**
 * The names of a group and the groups above it, joined: a subgroup shares its name with others easily.
 * Only the groups the person may filter by are known, which always includes the ones above their own.
 * A cycle in the parents (should not exist) ends the path instead of looping.
 */
export const getGroupFilterPathLabel = (group: TFilterableUserGroup, groupsById: Map<string, TFilterableUserGroup>) => {
  const names = [group.name];
  const seen = new Set([group.id]);
  let parentId = group.parent_id;
  while (parentId && !seen.has(parentId)) {
    const parent = groupsById.get(parentId);
    if (!parent) break;
    names.unshift(parent.name);
    seen.add(parent.id);
    parentId = parent.parent_id;
  }
  return names.join(PATH_SEPARATOR);
};

/** The label of a keyword, translated when a translator is given. */
export const getGroupFilterKeywordLabel = (keyword: string, t?: TGroupFilterTranslate): string => {
  if (keyword === GROUP_FILTER_KEYWORDS.MY_GROUPS) return t ? t("group_filter.my_groups") : "My groups";
  return t ? t("group_filter.no_group") : "No group";
};

/**
 * The options of a group filter: "My groups" and "No group" first, then the groups by their path label.
 * @param groups - The groups the person may filter by
 * @param t - Translates the keyword labels, they stay English without it
 */
export const getGroupFilterOptions = (
  groups: TFilterableUserGroup[],
  t?: TGroupFilterTranslate
): TGroupFilterOption[] => {
  const groupsById = new Map(groups.map((group) => [group.id, group]));
  const keywordOptions = Object.values(GROUP_FILTER_KEYWORDS).map((keyword) => ({
    value: keyword as string,
    label: getGroupFilterKeywordLabel(keyword, t),
    isKeyword: true,
  }));
  const groupOptions = groups
    .map((group) => ({
      value: group.id,
      label: getGroupFilterPathLabel(group, groupsById),
      isKeyword: false,
    }))
    .toSorted((a, b) => a.label.localeCompare(b.label, undefined, { numeric: true, sensitivity: "base" }));
  return [...keywordOptions, ...groupOptions];
};

/**
 * The label of an applied value: a keyword, a group, or null for a group the person may not see (any more).
 * @param value - A group id or a keyword
 * @param groups - The groups the person may filter by
 * @param t - Translates the keyword labels
 */
export const getGroupFilterValueLabel = (
  value: string,
  groups: TFilterableUserGroup[],
  t?: TGroupFilterTranslate
): string | null => {
  if (isGroupFilterKeyword(value)) return getGroupFilterKeywordLabel(value, t);
  const groupsById = new Map(groups.map((group) => [group.id, group]));
  const group = groupsById.get(value);
  return group ? getGroupFilterPathLabel(group, groupsById) : null;
};

/** What the module and cycle list endpoints return about the groups of a row, see the filterable groups contract. */
export type TGroupFilterable = {
  /** The groups the row is in, incl. the ones above them, restricted to the ones the requester may filter by. */
  group_ids?: string[];
  /** Whether the row is in any group at all. */
  has_group?: boolean;
  /** Whether the row is in one of the requester's groups. */
  in_my_groups?: boolean;
};

/**
 * Whether a module or cycle matches the group filter. The values are OR-ed: a group id the row is in,
 * "my_groups" for a row in a group of the requester, "none" for a row in no group.
 * No values match everything. A group the requester may not filter by is not in `group_ids`, so it matches nothing.
 */
export const matchesGroupFilter = (values: string[] | null | undefined, item: TGroupFilterable): boolean => {
  if (!values || values.length === 0) return true;
  const groupIds = new Set(item.group_ids ?? []);
  return values.some((value) => {
    if (value === GROUP_FILTER_KEYWORDS.MY_GROUPS) return item.in_my_groups === true;
    if (value === GROUP_FILTER_KEYWORDS.NONE) return item.has_group !== true;
    return groupIds.has(value);
  });
};
