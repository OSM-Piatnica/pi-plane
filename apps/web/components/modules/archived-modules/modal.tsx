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
import { useModule } from "@/hooks/store/use-module";
import { useAppRouter } from "@/hooks/use-app-router";

type Props = {
  workspaceSlug: string;
  projectId: string;
  moduleId: string;
  handleClose: () => void;
  isOpen: boolean;
  onSubmit?: () => Promise<void>;
};

export function ArchiveModuleModal(props: Props) {
  const { workspaceSlug, projectId, moduleId, isOpen, handleClose } = props;
  // router
  const router = useAppRouter();
  // states
  const [isArchiving, setIsArchiving] = useState(false);
  // store hooks
  const { getModuleNameById, archiveModule } = useModule();
  const { t } = useTranslation();

  const moduleName = getModuleNameById(moduleId);

  const onClose = () => {
    setIsArchiving(false);
    handleClose();
  };

  const handleArchiveModule = async () => {
    setIsArchiving(true);
    try {
      await archiveModule(workspaceSlug, projectId, moduleId);
      setToast({
        type: "success",
        title: t("module_ui.archive_success_title"),
        message: t("module_ui.archive_success_message"),
      });
      onClose();
      router.push(`/${workspaceSlug}/projects/${projectId}/modules`);
    } catch {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("module_ui.archive_error"),
      });
    } finally {
      setIsArchiving(false);
    }
  };

  return (
    <ConfirmDialog
      isOpen={isOpen}
      handleClose={onClose}
      handleSubmit={handleArchiveModule}
      isSubmitting={isArchiving}
      variant="primary"
      title={t("module_ui.archive_modal_title", { name: moduleName })}
      content={t("module_ui.archive_modal_description")}
      primaryButtonText={{ loading: t("common.archiving"), default: t("common.archive") }}
      secondaryButtonText={t("common.cancel")}
    />
  );
}
