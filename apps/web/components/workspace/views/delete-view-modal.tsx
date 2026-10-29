/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// Plane Imports
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { IWorkspaceView } from "@plane/types";
// hooks
import { useGlobalView } from "@/hooks/store/use-global-view";

type Props = {
  data: IWorkspaceView;
  isOpen: boolean;
  onClose: () => void;
};

export const DeleteGlobalViewModal = observer(function DeleteGlobalViewModal(props: Props) {
  const { data, isOpen, onClose } = props;
  // states
  const [isDeleteLoading, setIsDeleteLoading] = useState(false);
  // router
  const { workspaceSlug } = useParams();
  // store hooks
  const { deleteGlobalView } = useGlobalView();
  const { t } = useTranslation();
  const handleClose = () => onClose();

  const handleDeletion = async () => {
    if (!workspaceSlug) return;
    setIsDeleteLoading(true);

    try {
      await deleteGlobalView(workspaceSlug.toString(), data.id);
    } catch (_error) {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("app_text.workspace_views.delete_failed"),
      });
    }

    setIsDeleteLoading(false);
    handleClose();
    // remove filters from local storage
    localStorage.removeItem(`global_view_filters/${data.id}`);
  };

  return (
    <ConfirmDialog
      handleClose={handleClose}
      handleSubmit={handleDeletion}
      isSubmitting={isDeleteLoading}
      isOpen={isOpen}
      title={t("workspace_views.delete_view.title")}
      content={t("workspace_views.delete_view.content")}
    />
  );
});
