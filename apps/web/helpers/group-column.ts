/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Marks a cycle column that cannot take a drop because the cycle is completed. The column is built
 * where no translation is available, so the drag overlay turns this marker into the message.
 */
export const COMPLETED_CYCLE_DROP_ERROR = "completed_cycle";

// The priority and state-group columns are built from constants where no translation is available.
// Their ids are the fixed keys below (a user's own groups have uuid ids), so they are translated here.
const FIXED_COLUMN_NAME_KEYS = new Map<string, string>(
  Object.entries({
    None: "common.none",
    urgent: "issue.priority.urgent",
    high: "issue.priority.high",
    medium: "issue.priority.medium",
    low: "issue.priority.low",
    none: "common.none",
    backlog: "workspace_projects.state.backlog",
    unstarted: "workspace_projects.state.unstarted",
    started: "workspace_projects.state.started",
    completed: "workspace_projects.state.completed",
    cancelled: "app_text.state_groups.canceled",
  })
);

/**
 * The title to show for a group-by column. The empty "None" group, the priority groups and the state
 * group columns are built where no translation is available, so they are recognised by their id and
 * translated here.
 */
export const getGroupColumnName = (column: { id: string; name: string }, t: (key: string) => string): string => {
  const key = FIXED_COLUMN_NAME_KEYS.get(column.id);
  return key ? t(key) : column.name;
};
