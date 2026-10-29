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
 * Asks whether a work item that was just marked as a duplicate should be moved to the cancelled state. Mounted once;
 * the relation hooks open it after the relation is added.
 */
export const DuplicateCancelConfirmModal = observer(function DuplicateCancelConfirmModal() {
  const { t } = useTranslation();
  const { pendingDuplicateCancel, resolveDuplicateCancel } = useWorkflow();

  return (
    <ConfirmDialog
      isOpen={pendingDuplicateCancel !== null}
      variant="warning"
      title={t("issue.relation.duplicate_cancel.title")}
      content={t("issue.relation.duplicate_cancel.content", {
        issue: pendingDuplicateCancel?.issue ?? "",
        originals: pendingDuplicateCancel?.originals ?? "",
        state: pendingDuplicateCancel?.stateName ?? "",
      })}
      primaryButtonText={{ default: t("issue.relation.duplicate_cancel.confirm") }}
      secondaryButtonText={t("issue.relation.duplicate_cancel.keep")}
      isSubmitting={false}
      handleClose={() => resolveDuplicateCancel(false)}
      handleSubmit={() => resolveDuplicateCancel(true)}
    />
  );
});
