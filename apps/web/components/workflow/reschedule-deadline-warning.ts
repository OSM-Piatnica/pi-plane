/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TRelationRescheduleShift } from "@plane/types";

export type TRescheduleDeadlineWarning = {
  key: "issue.relation.reschedule.deadline_overrun" | "issue.relation.reschedule.deadline_overrun_more";
  params: { issue: string; count: number; previous?: number };
};

/**
 * The warning for a work item the offer would move past its due date, or null. The API counts the overrun in
 * working days of the item's project and sends it only when the shift makes the item pass its due date by more
 * than before; for an item that was late already it also sends the overrun it had.
 */
export const getRescheduleDeadlineWarning = (shift: TRelationRescheduleShift): TRescheduleDeadlineWarning | null => {
  const count = shift.deadline_overrun_days;
  if (!count || count <= 0) return null;
  const previous = shift.previous_deadline_overrun_days;
  if (previous && previous > 0)
    return { key: "issue.relation.reschedule.deadline_overrun_more", params: { issue: shift.ref, count, previous } };
  return { key: "issue.relation.reschedule.deadline_overrun", params: { issue: shift.ref, count } };
};
