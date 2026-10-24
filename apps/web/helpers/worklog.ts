/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserPermissions } from "@plane/constants";

// Mirror the limits of the API (a single entry is at most 24 hours)
export const MAX_WORKLOG_MINUTES = 24 * 60;
export const MAX_WORKLOG_DESCRIPTION_LENGTH = 5000;

/** Time logged on work items is confidential: project admins and members see it, guests do not. */
export const canViewWorklogsForRole = (role: number | undefined): boolean =>
  role === EUserPermissions.ADMIN || role === EUserPermissions.MEMBER;

/** Minutes as "2h 30m", "2h" or "45m". */
export const formatWorklogDuration = (minutes: number): string => {
  const total = Math.max(0, Math.floor(minutes || 0));
  const hours = Math.floor(total / 60);
  const rest = total % 60;
  if (hours && rest) return `${hours}h ${rest}m`;
  if (hours) return `${hours}h`;
  return `${rest}m`;
};

/**
 * Parses a duration typed by a person into minutes.
 * Accepts "2h 30m", "2h30m", "2h", "30m", "45 min", "1.5h", "1,5h" and plain minutes ("90").
 * Returns null for anything else and for zero.
 */
export const parseWorklogDuration = (input: string): number | null => {
  const value = input.trim().toLowerCase();
  if (!value) return null;
  if (/^\d+$/.test(value)) {
    const minutes = Number.parseInt(value, 10);
    return minutes > 0 ? minutes : null;
  }
  const match = /^(?:(\d+(?:[.,]\d+)?)\s*h)?\s*(?:(\d+)\s*m(?:in)?s?)?$/.exec(value);
  if (!match || (match[1] === undefined && match[2] === undefined)) return null;
  const hours = match[1] ? Number.parseFloat(match[1].replace(",", ".")) : 0;
  const mins = match[2] ? Number.parseInt(match[2], 10) : 0;
  const minutes = Math.round(hours * 60 + mins);
  return minutes > 0 ? minutes : null;
};

/** The minutes of a typed duration, or null when it cannot be logged (unreadable, zero or over 24 hours). */
export const parseLoggableWorklogDuration = (input: string): number | null => {
  const minutes = parseWorklogDuration(input);
  return minutes === null || minutes > MAX_WORKLOG_MINUTES ? null : minutes;
};
