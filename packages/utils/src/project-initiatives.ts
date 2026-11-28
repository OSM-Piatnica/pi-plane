/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * The project list by initiative (roadmap F3, `docs/initiatives.md`). A project carries the ids of the
 * initiatives it is linked to (`initiative_ids`); goals are reached through their initiatives.
 */

/** The filter value and the group key for the projects that are in no initiative */
export const PROJECT_NO_INITIATIVE = "none";

/** The initiative ids of each goal: a goal in the filter stands for these */
export type TInitiativeIdsByGoal = Record<string, readonly string[]>;

/**
 * Whether a project matches an initiative filter. The values are initiative ids, goal ids and
 * `PROJECT_NO_INITIATIVE`; a project matches when it is in any of them (a goal: in any of its
 * initiatives), or is in no initiative and `PROJECT_NO_INITIATIVE` is asked for. An empty filter matches all.
 */
export const matchesInitiativeFilter = (
  values: readonly string[] | null | undefined,
  projectInitiativeIds: readonly string[] | null | undefined,
  initiativeIdsByGoal: TInitiativeIdsByGoal = {}
): boolean => {
  if (!values || values.length === 0) return true;
  const own = projectInitiativeIds ?? [];
  if (own.length === 0) return values.includes(PROJECT_NO_INITIATIVE);
  const wanted = new Set<string>();
  for (const value of values) {
    if (value === PROJECT_NO_INITIATIVE) continue;
    wanted.add(value);
    for (const initiativeId of initiativeIdsByGoal[value] ?? []) wanted.add(initiativeId);
  }
  return own.some((initiativeId) => wanted.has(initiativeId));
};

export type TProjectInitiativeGroup = {
  /** An initiative id, or `PROJECT_NO_INITIATIVE` */
  key: string;
  projectIds: string[];
};

/**
 * Splits an ordered list of projects into one group per initiative, a project in several initiatives
 * going into each of their groups, and a last group of the projects in no initiative. Projects keep
 * their order in every group; groups without projects are left out.
 * @param projects - The projects as the list shows them, in their order
 * @param initiativeOrder - The initiatives in the order of their groups; an id a project names that is
 *   not in it (not loaded yet) gets a group after them, so the project still shows
 */
export const groupProjectsByInitiative = (
  projects: readonly { id: string; initiative_ids?: readonly string[] | null }[],
  initiativeOrder: readonly string[]
): TProjectInitiativeGroup[] => {
  const groups = new Map<string, string[]>(initiativeOrder.map((initiativeId) => [initiativeId, []]));
  const none: string[] = [];
  for (const project of projects) {
    const initiativeIds = project.initiative_ids ?? [];
    if (initiativeIds.length === 0) {
      none.push(project.id);
      continue;
    }
    for (const initiativeId of new Set(initiativeIds)) {
      const group = groups.get(initiativeId);
      if (group) group.push(project.id);
      else groups.set(initiativeId, [project.id]);
    }
  }
  const result: TProjectInitiativeGroup[] = [];
  for (const [key, projectIds] of groups) if (projectIds.length > 0) result.push({ key, projectIds });
  if (none.length > 0) result.push({ key: PROJECT_NO_INITIATIVE, projectIds: none });
  return result;
};
