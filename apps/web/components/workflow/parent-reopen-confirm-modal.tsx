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
 * Asks whether reopening a finished work item should also reopen its completed parents. Mounted once; the
 * issue store opens it when the API refuses an update that needs this confirmation.
 */
export const ParentReopenConfirmModal = observer(function ParentReopenConfirmModal() {
  const { t } = useTranslation();
  const { pendingParentReopen, resolveParentReopen } = useWorkflow();
  const parents = pendingParentReopen ?? [];

  return (
    <ConfirmDialog
      isOpen={pendingParentReopen !== null}
      variant="warning"
      title={t("project_settings.workflows.rules.reopen_parent.title")}
      content={t("project_settings.workflows.rules.reopen_parent.content", {
        count: parents.length,
        names: parents.map((parent) => parent.name).join(", "),
      })}
      primaryButtonText={{ default: t("project_settings.workflows.rules.reopen_parent.confirm") }}
      isSubmitting={false}
      handleClose={() => resolveParentReopen(false)}
      handleSubmit={() => resolveParentReopen(true)}
    />
  );
});
