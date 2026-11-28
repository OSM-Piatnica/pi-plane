/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssue } from "@plane/types";
import { isMilestoneType } from "@plane/utils";
import { getMilestoneMarkerDates } from "@/helpers/milestone";
import { useWorkspaceIssueTypes } from "@/hooks/use-workspace-issue-types";

/** The dates of a milestone's timeline marker; null for any other work item and for a rolled-up bar. */
export function useMilestoneMarkerDates(
  workspaceSlug: string | undefined,
  issue: TIssue | undefined,
  isRolledUp: boolean
) {
  const { typeMap } = useWorkspaceIssueTypes(workspaceSlug);
  const issueType = issue?.type_id ? typeMap[issue.type_id] : undefined;
  return getMilestoneMarkerDates(issue, !isRolledUp && isMilestoneType(issueType));
}
