/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
// ui
import { useTranslation } from "@plane/i18n";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
// hooks
import { useCycle } from "@/hooks/store/use-cycle";
import { useAppRouter } from "@/hooks/use-app-router";

type Props = {
  workspaceSlug: string;
  projectId: string;
  cycleId: string;
  handleClose: () => void;
  isOpen: boolean;
  onSubmit?: () => Promise<void>;
};

export function ArchiveCycleModal(props: Props) {
  const { workspaceSlug, projectId, cycleId, isOpen, handleClose } = props;
  // router
  const router = useAppRouter();
  // states
  const [isArchiving, setIsArchiving] = useState(false);
  // store hooks
  const { getCycleNameById, archiveCycle } = useCycle();
  const { t } = useTranslation();

  const cycleName = getCycleNameById(cycleId);

  const onClose = () => {
    setIsArchiving(false);
    handleClose();
  };

  const handleArchiveCycle = async () => {
    setIsArchiving(true);
    await archiveCycle(workspaceSlug, projectId, cycleId)
      .then(() => {
        setToast({
          type: "success",
          title: t("cycle_ui.archive_success_title"),
          message: t("cycle_ui.archive_success_message"),
        });
        onClose();
        router.push(`/${workspaceSlug}/projects/${projectId}/cycles`);
        return;
      })
      .catch(() => {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: t("cycle_ui.archive_error"),
        });
      })
      .finally(() => setIsArchiving(false));
  };

  return (
    <ConfirmDialog
      isOpen={isOpen}
      handleClose={onClose}
      handleSubmit={handleArchiveCycle}
      isSubmitting={isArchiving}
      variant="primary"
      title={t("cycle_ui.archive_modal_title", { name: cycleName ?? "" })}
      content={t("cycle_ui.archive_modal_description")}
      primaryButtonText={{ loading: t("common.archiving"), default: t("common.archive") }}
      secondaryButtonText={t("common.cancel")}
    />
  );
}
