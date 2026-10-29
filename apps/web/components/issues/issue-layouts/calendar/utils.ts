/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TIssue } from "@plane/types";
import type { TCalendarLayer } from "@/store/issue/helpers/calendar-layers";
import { getCalendarDragPatch } from "@/store/issue/helpers/calendar-layers";

export const handleDragDrop = async (
  issueId: string,
  sourceDate: string,
  destinationDate: string,
  workspaceSlug: string | undefined,
  projectId: string | undefined,
  updateIssue?: (projectId: string, issueId: string, data: Partial<TIssue>) => Promise<void>,
  layer: TCalendarLayer = "deadlines",
  issue?: Pick<TIssue, "start_date" | "finish_date" | "target_date">
) => {
  if (!workspaceSlug || !projectId || !updateIssue) return;

  if (sourceDate === destinationDate) return;

  // Scheduled layer: start and finish move together (due untouched). Deadlines layer: only the due date moves.
  const patch = getCalendarDragPatch(layer, issue ?? {}, sourceDate, destinationDate);
  if (!patch) return;

  return await updateIssue(projectId, issueId, patch);
};
