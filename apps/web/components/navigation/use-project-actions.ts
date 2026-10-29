/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { setToast } from "@plane/blocks/toast";
import { copyUrlToClipboard } from "@plane/utils";
import type { TNavigationItem } from "@/components/navigation/tab-navigation-root";
import { useTranslation } from "@plane/i18n";

type UseProjectActionsProps = {
  workspaceSlug: string;
  projectId: string;
  activeItem?: TNavigationItem;
};

export const useProjectActions = ({ workspaceSlug, projectId, activeItem }: UseProjectActionsProps) => {
  const { t } = useTranslation();
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [leaveProjectModalOpen, setLeaveProjectModalOpen] = useState(false);

  const handleLeaveProject = useCallback(() => {
    setLeaveProjectModalOpen(true);
  }, []);

  const handleCopyText = useCallback(async () => {
    const pathToCopy = activeItem?.href ?? `/${workspaceSlug}/projects/${projectId}/issues`;

    try {
      await copyUrlToClipboard(pathToCopy);
      setToast({
        type: "info",
        title: t("common.link_copied"),
        message: t("app_text.navigation.project_link_copied"),
      });
    } catch (_error) {
      setToast({
        type: "error",
        title: t("app_text.navigation.copy_failed"),
        message: t("app_text.navigation.copy_failed_message"),
      });
    }
  }, [activeItem, projectId, t, workspaceSlug]);

  const handlePublishModal = useCallback((open: boolean) => {
    setPublishModalOpen(open);
  }, []);

  const handleLeaveProjectModal = useCallback((open: boolean) => {
    setLeaveProjectModalOpen(open);
  }, []);

  return {
    publishModalOpen,
    leaveProjectModalOpen,
    handleLeaveProject,
    handleCopyText,
    handlePublishModal,
    handleLeaveProjectModal,
  };
};
