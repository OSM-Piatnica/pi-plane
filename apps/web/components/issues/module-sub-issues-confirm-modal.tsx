/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { useWorkflow } from "@/hooks/store/use-workflow";

/**
 * Asks whether the sub-work items of a work item move into (or out of) a module together with it. Mounted once;
 * the issue store opens it. Dismissing it means "only the work item", as it was before the question existed.
 */
export const ModuleSubIssuesConfirmModal = observer(function ModuleSubIssuesConfirmModal() {
  const { t } = useTranslation();
  const { pendingSubIssuesChoice, resolveSubIssues } = useWorkflow();
  const mode = pendingSubIssuesChoice?.mode ?? "add";
  const names = pendingSubIssuesChoice?.names ?? [];

  return (
    <ConfirmDialog
      isOpen={pendingSubIssuesChoice !== null}
      variant="warning"
      title={t(`module.sub_issues.${mode}.title`)}
      content={t(`module.sub_issues.${mode}.content`, { count: names.length, names: names.join(", ") })}
      primaryButtonText={{ default: t(`module.sub_issues.${mode}.confirm`) }}
      secondaryButtonText={t(`module.sub_issues.${mode}.decline`)}
      isSubmitting={false}
      handleClose={() => resolveSubIssues(false)}
      handleSubmit={() => resolveSubIssues(true)}
    />
  );
});
