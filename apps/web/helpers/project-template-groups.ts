/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TProjectTemplateGroup, TUserGroup } from "@plane/types";

export const GROUP_PATH_SEPARATOR = " / ";

/** The roles a template can give a group: Member (15) or Guest (5), never Admin. */
export const TEMPLATE_GROUP_ROLES: (15 | 5)[] = [15, 5];

export type TTemplateGroupRow = {
  group: string;
  path: string;
  role: 15 | 5;
};

/** {group id: "Parent / Child"} for every group, the way the server writes paths into a template. */
export const getGroupPaths = (groups: Pick<TUserGroup, "id" | "name" | "parent">[]): Map<string, string> => {
  const byId = new Map(groups.map((group) => [group.id, group]));
  const paths = new Map<string, string>();
  for (const group of groups) {
    const names: string[] = [];
    const seen = new Set<string>();
    let current: Pick<TUserGroup, "id" | "name" | "parent"> | undefined = group;
    while (current && !seen.has(current.id)) {
      seen.add(current.id);
      names.push(current.name);
      current = current.parent ? byId.get(current.parent) : undefined;
    }
    paths.set(group.id, names.toReversed().join(GROUP_PATH_SEPARATOR));
  }
  return paths;
};

export const isTemplateGroupRole = (role: number): role is 15 | 5 => role === 15 || role === 5;

/** The groups of a template payload as editor rows; entries without an id or with a role a group cannot have are left out. */
export const mapTemplateGroupsFromPayload = (groups: TProjectTemplateGroup[] | undefined): TTemplateGroupRow[] =>
  (groups ?? [])
    .filter((entry) => !!entry.group && isTemplateGroupRole(Number(entry.role)))
    .map((entry) => ({ group: entry.group as string, path: entry.path ?? "", role: entry.role }));

/**
 * The payload entries for the editor rows: the id with the path next to it, so a downloaded template can be uploaded into
 * another workspace (which matches groups by path). A path is taken from the group's current one when it still exists.
 */
export const buildTemplateGroupsPayload = (
  rows: TTemplateGroupRow[],
  paths: Map<string, string>
): TProjectTemplateGroup[] => {
  const seen = new Set<string>();
  const entries: TProjectTemplateGroup[] = [];
  for (const row of rows) {
    if (!row.group || seen.has(row.group) || !isTemplateGroupRole(row.role)) continue;
    seen.add(row.group);
    entries.push({ group: row.group, path: paths.get(row.group) ?? row.path, role: row.role });
  }
  return entries;
};

/** The workspace's groups that the template does not list yet, by path. */
export const getAddableTemplateGroups = (
  groups: Pick<TUserGroup, "id" | "name" | "parent">[],
  rows: Pick<TTemplateGroupRow, "group">[]
): { id: string; path: string }[] => {
  const listed = new Set(rows.map((row) => row.group));
  const paths = getGroupPaths(groups);
  return groups
    .filter((group) => !listed.has(group.id))
    .map((group) => ({ id: group.id, path: paths.get(group.id) ?? group.name }))
    .toSorted((a, b) => a.path.localeCompare(b.path));
};
