/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { differenceInCalendarDays } from "date-fns";
import type { TIssue } from "@plane/types";
import { getDate } from "@plane/utils";

/** A milestone is late when its finish date (the diamond) is after its due date. */
export const isMilestoneLate = (finishDate: string | null | undefined, dueDate: string | null | undefined): boolean => {
  const finish = getDate(finishDate);
  const due = getDate(dueDate);
  if (!finish || !due) return false;
  return differenceInCalendarDays(finish, due) > 0;
};

export type TMilestoneDates = { start?: string | null; finish?: string | null; due?: string | null };

/** The dates a milestone's timeline marker shows, or null when the work item is drawn otherwise. */
export const getMilestoneMarkerDates = (
  issue: Pick<TIssue, "start_date" | "finish_date" | "target_date"> | undefined,
  isMilestone: boolean
): TMilestoneDates | null =>
  isMilestone && issue?.finish_date
    ? { start: issue.start_date, finish: issue.finish_date, due: issue.target_date }
    : null;
