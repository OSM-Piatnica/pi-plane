/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IProject, TIssueActivity, TRelationRescheduleOffer, TRelationRescheduleShift } from "@plane/types";
import { generateWorkItemLink } from "@plane/utils";

/**
 * The offer in an API error, when the API answered that the person has to agree first: dependents to move, sub-work
 * items that can follow, or both. Null for any other error. An answer from before sub-work items could follow has
 * only `shifts`.
 */
export const getRescheduleOffer = (error: unknown): TRelationRescheduleOffer | null => {
  const body = error as Partial<TRelationRescheduleOffer> & { error_code?: string };
  if (body?.error_code !== "relation_reschedule_available") return null;
  const shifts = body.shifts ?? [];
  const subItems = body.sub_items ?? [];
  if (!shifts.length && !subItems.length) return null;
  return { shifts, sub_items: subItems, shifts_with_sub_items: body.shifts_with_sub_items ?? shifts };
};

/** How a date change asks for, or answers, the offer to move other work items along. */
export type TRescheduleRequestOptions = {
  /** The person agreed that the dependents move */
  shiftDependents?: boolean;
  /** Offer the sub-work items of a moved parent as well, instead of saving the change without them */
  offerSubItems?: boolean;
  /** The answer about the sub-work items: true to move them, false to leave them; left out before the offer */
  moveSubItems?: boolean;
};

/** The request flags for these options (`shift_dependents`, `offer_sub_items`, `move_sub_items`). */
export const rescheduleFlags = (options?: TRescheduleRequestOptions) => ({
  ...(options?.shiftDependents ? { shift_dependents: true } : {}),
  ...(options?.offerSubItems ? { offer_sub_items: true } : {}),
  ...(options?.moveSubItems !== undefined ? { move_sub_items: options.moveSubItems } : {}),
});

/** The dependents that move with the answer given: those of the plan with or without the sub-work items. */
export const getRescheduleDependents = (
  offer: TRelationRescheduleOffer,
  moveSubItems: boolean
): TRelationRescheduleShift[] => (moveSubItems && offer.sub_items.length ? offer.shifts_with_sub_items : offer.shifts);

/** Every work item that moves besides the changed ones, with the answer given: to bring up to date afterwards. */
export const getRescheduleMoves = (
  offer: TRelationRescheduleOffer,
  moveSubItems: boolean
): TRelationRescheduleShift[] => [
  ...getRescheduleDependents(offer, moveSubItems),
  ...(moveSubItems ? offer.sub_items : []),
];

/** Mirrors the default of `Project.is_reschedule_offer_enabled`. */
export const RESCHEDULE_OFFER_DEFAULT = true;

/**
 * Whether the project offers to move dependent work items when a date change breaks a relation. A project loaded
 * before the flag existed, or not loaded yet, counts as on.
 */
export const isRescheduleOfferEnabled = (
  project: Partial<Pick<IProject, "is_reschedule_offer_enabled">> | undefined | null
): boolean => project?.is_reschedule_offer_enabled ?? RESCHEDULE_OFFER_DEFAULT;

export type TShiftCauseLink = { ref: string; href: string };

/**
 * The work item whose change moved this one along, for a start or finish date entry written by a shift of dependents:
 * its reference (`WDR-12`) and the link to it. Undefined for any other entry, and when that work item is gone.
 * `workspaceSlug` stands in for an entry that carries no workspace detail.
 */
export const getShiftCause = (
  activity:
    | {
        field?: string | null;
        shift_cause?: TIssueActivity["shift_cause"];
        workspace_detail?: { slug?: string | null } | null;
      }
    | undefined,
  workspaceSlug?: string
): TShiftCauseLink | undefined => {
  const cause = activity?.shift_cause;
  if (!activity || !cause) return undefined;
  if (activity.field !== "start_date" && activity.field !== "finish_date") return undefined;
  workspaceSlug = workspaceSlug || activity.workspace_detail?.slug || undefined;
  if (!workspaceSlug || !cause.project_identifier || cause.sequence_id === null || cause.sequence_id === undefined)
    return undefined;
  return {
    ref: `${cause.project_identifier}-${cause.sequence_id}`,
    href: generateWorkItemLink({
      workspaceSlug,
      projectId: cause.project_id,
      issueId: cause.id,
      projectIdentifier: cause.project_identifier,
      sequenceId: cause.sequence_id,
    }),
  };
};
