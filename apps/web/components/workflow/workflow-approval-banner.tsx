/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { getStateName } from "@/helpers/state-name";
import { setPromiseToast } from "@plane/blocks/toast";
import { Button } from "@makeplane/propel/components/button";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useWorkflow } from "@/hooks/store/use-workflow";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

export const WorkflowApprovalBanner = observer(function WorkflowApprovalBanner(props: Props) {
  const { workspaceSlug, projectId, issueId } = props;
  const { t } = useTranslation();
  const workflowStore = useWorkflow();
  const { fetchIssue } = useIssueDetail();

  const status = workflowStore.getIssueWorkflowStatus(issueId);
  const pendingApproval = status?.pending_approval;

  useEffect(() => {
    workflowStore.fetchIssueWorkflowStatus(workspaceSlug, projectId, issueId).catch(() => undefined);
  }, [workspaceSlug, projectId, issueId, workflowStore]);

  if (status && !status.is_workflow_enabled) return null;

  const hasPendingApproval =
    Boolean(status?.blocker_message) ||
    pendingApproval?.status === "pending" ||
    Boolean(pendingApproval?.id && !pendingApproval.resolved_at);

  if (!hasPendingApproval) return null;

  const canResolve = Boolean(pendingApproval?.id);

  const handleResolve = async (action: "approve" | "reject") => {
    if (!pendingApproval?.id) return;
    const promise = workflowStore
      .resolveApproval(workspaceSlug, projectId, issueId, pendingApproval.id, action)
      .then(() => fetchIssue(workspaceSlug, projectId, issueId));

    setPromiseToast(promise, {
      loading: t("project_settings.workflows.resolving_approval"),
      success: {
        title: t("common.success"),
        message: () =>
          action === "approve"
            ? t("project_settings.workflows.approved_success")
            : t("project_settings.workflows.rejected_success"),
      },
      error: {
        title: t("common.error.label"),
        message: () => t("project_settings.workflows.approval_error"),
      },
    });
    await promise;
  };

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-accent-strong bg-accent-primary/10 px-4 py-3">
      <div>
        <p className="text-13 font-medium text-primary">{t("project_settings.workflows.pending_approval_title")}</p>
        <p className="mt-0.5 text-11 text-secondary">
          {t("project_settings.workflows.pending_approval_description", {
            from: getStateName(pendingApproval?.source_state_detail?.name ?? "", t),
            to: getStateName(pendingApproval?.approve_state_detail?.name ?? "", t),
          })}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Button
          stretch="auto"
          variant="secondary"
          size="sm"
          onClick={() => handleResolve("reject")}
          disabled={!canResolve}
          label={t("reject")}
        />
        <Button
          stretch="auto"
          variant="primary"
          size="sm"
          onClick={() => handleResolve("approve")}
          disabled={!canResolve}
          label={t("approve")}
        />
      </div>
    </div>
  );
});
