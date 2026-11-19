/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IProject, TIssueActivity } from "@plane/types";
import { generateWorkItemLink } from "@plane/utils";

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
 */
export const getShiftCause = (
  activity: Pick<TIssueActivity, "field" | "shift_cause" | "workspace_detail"> | undefined
): TShiftCauseLink | undefined => {
  const cause = activity?.shift_cause;
  if (!activity || !cause) return undefined;
  if (activity.field !== "start_date" && activity.field !== "finish_date") return undefined;
  const workspaceSlug = activity.workspace_detail?.slug;
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
