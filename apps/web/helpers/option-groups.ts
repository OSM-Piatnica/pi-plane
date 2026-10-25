/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TOptionGroupItem = { key: string; label: string };

export type TOptionGroup = {
  key: string;
  label: string;
  options: TOptionGroupItem[];
};

export type TGroupSelectionState = "all" | "some" | "none";

/** Every option key of the groups, in order. */
export const getOptionKeys = (groups: TOptionGroup[]): string[] =>
  groups.flatMap((group) => group.options.map((option) => option.key));

/** Whether all, some or none of a group's options are selected. */
export const getGroupSelectionState = (group: TOptionGroup, selected: string[]): TGroupSelectionState => {
  const chosen = new Set(selected);
  const count = group.options.filter((option) => chosen.has(option.key)).length;
  if (count === 0) return "none";
  return count === group.options.length ? "all" : "some";
};

/** Selects every option of a group, or clears them all when the group is already fully selected. */
export const toggleGroup = (group: TOptionGroup, selected: string[]): string[] => {
  const groupKeys = new Set(group.options.map((option) => option.key));
  const rest = selected.filter((key) => !groupKeys.has(key));
  return getGroupSelectionState(group, selected) === "all" ? rest : [...rest, ...groupKeys];
};

/** Switches one option on or off. */
export const toggleOption = (key: string, selected: string[]): string[] =>
  selected.includes(key) ? selected.filter((item) => item !== key) : [...selected, key];
