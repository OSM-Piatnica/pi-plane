/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TGanttRows = {
  /** Row order: every top-level id, each followed by the sub-work items of the ones that are expanded. */
  ids: string[];
  /** Indentation level per id (0 for top-level rows). */
  levelById: Record<string, number>;
};

/**
 * Lays out the rows of the timeline: the listed work items, with the sub-work items of the expanded ones
 * (recursively) inserted right below their parent. A work item that is already a top-level row, or that
 * was placed under another parent, is not repeated, which also keeps parent cycles from looping.
 */
export const flattenGanttRows = (
  topLevelIds: string[],
  expandedIds: ReadonlySet<string>,
  getChildIds: (id: string) => string[] | undefined
): TGanttRows => {
  const ids: string[] = [];
  const levelById: Record<string, number> = {};
  const placed = new Set<string>(topLevelIds);

  const place = (id: string, level: number) => {
    ids.push(id);
    levelById[id] = level;
    if (!expandedIds.has(id)) return;
    for (const childId of getChildIds(id) ?? []) {
      if (placed.has(childId)) continue;
      placed.add(childId);
      place(childId, level + 1);
    }
  };

  // top-level ids are all marked as placed up front, so a child never takes the spot of a listed work item
  for (const id of topLevelIds) place(id, 0);

  return { ids, levelById };
};
