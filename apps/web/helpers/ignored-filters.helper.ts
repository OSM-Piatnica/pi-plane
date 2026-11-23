/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Sometimes the server leaves a filter out of a list instead of failing the request (the critical path filter where
 * the schedule analysis is cut off at its limit). It names those filters in this response header, comma separated.
 */
export const IGNORED_FILTERS_HEADER = "x-ignored-filters";

/** Sent on `window` when a response says filters were left out; `detail` is the list of their names. */
export const IGNORED_FILTERS_EVENT = "plane:ignored-filters";

// lists are fetched again and again (paging, grouping, edits): tell the person once in a while, not each time
export const IGNORED_FILTERS_NOTICE_INTERVAL_MS = 60_000;

/** The filter names in the value of the header; anything that is not a name is dropped. */
export const parseIgnoredFilters = (value: unknown): string[] =>
  typeof value === "string"
    ? [
        ...new Set(
          value
            .split(",")
            .map((name) => name.trim())
            .filter((name) => /^[a-z_]+$/.test(name))
        ),
      ]
    : [];

/** Whether a notice about `name` is due: not shown yet, or not for a while. Records the time when it is due. */
export const isIgnoredFilterNoticeDue = (
  name: string,
  lastShown: Map<string, number>,
  now: number = Date.now()
): boolean => {
  const last = lastShown.get(name);
  if (last !== undefined && now - last < IGNORED_FILTERS_NOTICE_INTERVAL_MS) return false;
  lastShown.set(name, now);
  return true;
};

/** Pass on what a response says about left-out filters to whoever listens (`IgnoredFiltersNotice`). */
export const announceIgnoredFilters = (headers: unknown): void => {
  if (typeof window === "undefined" || !headers || typeof headers !== "object") return;
  const value = (headers as Record<string, unknown>)[IGNORED_FILTERS_HEADER];
  const names = parseIgnoredFilters(value);
  if (names.length > 0) window.dispatchEvent(new CustomEvent(IGNORED_FILTERS_EVENT, { detail: names }));
};
