/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Every project starts with these states, created by the API with English names that are stored as data
// ("To do" for new projects, "Todo" for ones created before). They are translated where they are shown;
// a state the user renamed or created keeps its own name.
const DEFAULT_STATE_NAME_KEYS = new Map<string, string>(
  Object.entries({
    Backlog: "default_state_names.backlog",
    Todo: "default_state_names.todo",
    "To do": "default_state_names.todo",
    "In Progress": "default_state_names.in_progress",
    Done: "default_state_names.done",
    Cancelled: "default_state_names.cancelled",
    Triage: "default_state_names.triage",
  })
);

/** The name to show for a state: the translated one for the English default names, its own name otherwise. */
export const getStateName = (name: string, t: (key: string) => string): string => {
  const key = DEFAULT_STATE_NAME_KEYS.get(name);
  return key ? t(key) : name;
};
