/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the hierarchy folding of inomotech-foss/paperplane (AGPL-3.0-only).
 * See the LICENSE file for details.
 */

/**
 * Which rows of the timeline show their sub-work items.
 *
 * `depth` is how many levels show by default: `1` only the top level ("collapse all"), `2` the top level and its
 * sub-work items, `null` every level ("expand all"). `overrides` holds the rows a person folded or unfolded by hand,
 * which win over the default until the next "expand all", "collapse all" or level choice.
 */
export type TGanttExpansion = {
  depth: number | null;
  overrides: Record<string, boolean>;
};

export const DEFAULT_GANTT_EXPANSION: TGanttExpansion = { depth: 1, overrides: {} };

/** Whether a row at `level` (0 for a top-level row) shows its sub-work items. */
export const isGanttRowExpanded = (expansion: TGanttExpansion, id: string, level: number) =>
  expansion.overrides[id] ?? (expansion.depth === null || level < expansion.depth - 1);

/** Fold or unfold one row by hand. */
export const toggleGanttRow = (expansion: TGanttExpansion, id: string, isExpanded: boolean): TGanttExpansion => ({
  ...expansion,
  overrides: { ...expansion.overrides, [id]: !isExpanded },
});

/** Show `depth` levels everywhere (null: all), forgetting the rows folded or unfolded by hand. */
export const showGanttLevels = (depth: number | null): TGanttExpansion => ({ depth, overrides: {} });

export type TGanttRows = {
  /** Row order: every top-level id, each followed by the sub-work items of the ones that are expanded. */
  ids: string[];
  /** Indentation level per id (0 for top-level rows). */
  levelById: Record<string, number>;
  /** The rows that show their sub-work items. */
  expandedIds: Set<string>;
  /** Expanded rows whose sub-work items are not loaded yet (`getChildIds` answers undefined for them). */
  unloadedExpandedIds: string[];
};

/**
 * Lays out the rows of the timeline: the listed work items, with the sub-work items of the expanded ones
 * (recursively) inserted right below their parent. A work item that is already a top-level row, or that
 * was placed under another parent, is not repeated, which also keeps parent cycles from looping.
 *
 * `isExpanded` is a set of expanded ids, or a function of the id and its level.
 */
export const flattenGanttRows = (
  topLevelIds: string[],
  isExpanded: ReadonlySet<string> | ((id: string, level: number) => boolean),
  getChildIds: (id: string) => string[] | undefined
): TGanttRows => {
  const ids: string[] = [];
  const levelById: Record<string, number> = {};
  const expandedIds = new Set<string>();
  const unloadedExpandedIds: string[] = [];
  const placed = new Set<string>(topLevelIds);
  const expanded = typeof isExpanded === "function" ? isExpanded : (id: string) => isExpanded.has(id);

  const place = (id: string, level: number) => {
    ids.push(id);
    levelById[id] = level;
    if (!expanded(id, level)) return;
    expandedIds.add(id);
    const childIds = getChildIds(id);
    if (childIds === undefined) {
      unloadedExpandedIds.push(id);
      return;
    }
    for (const childId of childIds) {
      if (placed.has(childId)) continue;
      placed.add(childId);
      place(childId, level + 1);
    }
  };

  // top-level ids are all marked as placed up front, so a child never takes the spot of a listed work item
  for (const id of topLevelIds) place(id, 0);

  return { ids, levelById, expandedIds, unloadedExpandedIds };
};
