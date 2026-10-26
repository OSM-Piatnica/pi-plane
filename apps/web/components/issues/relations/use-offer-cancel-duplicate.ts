/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
import type { TIssueRelationTypes, TIssueServiceType } from "@plane/types";
import { EIssueServiceType } from "@plane/types";
// helpers
import { getIssueApiErrorMessage } from "@/helpers/issue-api-error";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useWorkflow } from "@/hooks/store/use-workflow";

/**
 * A work item marked as a duplicate is usually done with: after the relation is added, offers to move it to the
 * project's cancelled state. It stays linked and visible either way. Nothing is offered for other relations, when
 * the work item is already completed or cancelled, or when the project has no cancelled state.
 */
export const useOfferCancelDuplicate = (issueServiceType: TIssueServiceType = EIssueServiceType.ISSUES) => {
  const { t } = useTranslation();
  const {
    issue: { getIssueById },
    updateIssue,
  } = useIssueDetail(issueServiceType);
  const { getStateById, getProjectStates } = useProjectState();
  const { getProjectById } = useProject();
  const { confirmDuplicateCancel } = useWorkflow();

  return useCallback(
    async (
      workspaceSlug: string,
      projectId: string,
      issueId: string,
      relationKey: TIssueRelationTypes,
      originalIds: string[]
    ) => {
      if (relationKey !== "duplicate") return;
      const issue = getIssueById(issueId);
      if (!issue) return;

      const currentGroup = getStateById(issue.state_id)?.group;
      if (currentGroup === "completed" || currentGroup === "cancelled") return;
      const cancelledState = [...(getProjectStates(projectId) ?? [])]
        .filter((state) => state.group === "cancelled")
        .sort((a, b) => a.sequence - b.sequence)[0];
      if (!cancelledState) return;

      const reference = (id: string) => {
        const item = getIssueById(id);
        if (!item) return "";
        const identifier = item.project_id ? getProjectById(item.project_id)?.identifier : undefined;
        return `${identifier ?? ""}-${item.sequence_id}`;
      };

      const confirmed = await confirmDuplicateCancel({
        issue: `${reference(issueId)} ${issue.name}`.trim(),
        originals: originalIds.map(reference).filter(Boolean).join(", "),
        stateName: cancelledState.name,
      });
      if (!confirmed) return;

      try {
        await updateIssue(workspaceSlug, projectId, issueId, { state_id: cancelledState.id });
      } catch (error) {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: getIssueApiErrorMessage(error, t("issue.relation.duplicate_cancel.failed"), t),
        });
      }
    },
    [confirmDuplicateCancel, getIssueById, getProjectById, getProjectStates, getStateById, t, updateIssue]
  );
};
