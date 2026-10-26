/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Saturday and Sunday, numbered like `Date.getDay()` (0 = Sunday ... 6 = Saturday). */
export const DEFAULT_WEEKEND_DAYS: readonly number[] = [0, 6];

type TWeekendDaySources = {
  /** The person's own list; null or undefined when they follow the workspace. */
  profile?: number[] | null;
  /** The project being viewed. Leave it out when no project is, e.g. on My work or in a workspace view. */
  project?: { weekend_days?: number[] } | null;
  workspace?: number[] | null;
};

/**
 * The days to treat as non-working time. Inside a project its own days apply, so everyone sees the same shading and
 * the same durations; elsewhere the person's own list, else the workspace's.
 */
export const resolveWeekendDays = ({ profile, project, workspace }: TWeekendDaySources): number[] => {
  if (project) return project.weekend_days ?? workspace ?? [...DEFAULT_WEEKEND_DAYS];
  return profile ?? workspace ?? [...DEFAULT_WEEKEND_DAYS];
};

/** Whether a date, or a weekday number, falls on one of the days. */
export const isWeekendDay = (date: Date | number, weekendDays: number[]): boolean =>
  weekendDays.includes(typeof date === "number" ? date : date.getDay());
