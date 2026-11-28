/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TInitiative } from "@plane/types";
import { getInitiativeErrorMessage } from "@/helpers/initiatives";
import { useInitiative } from "@/hooks/store/use-initiative";
import { useAppRouter } from "@/hooks/use-app-router";

/** Deletes a goal (its initiatives stay, without a goal) or an initiative (its links and updates go) */
export const DeleteInitiativeModal = observer(function DeleteInitiativeModal(props: {
  workspaceSlug: string;
  initiative: TInitiative;
  isOpen: boolean;
  onClose: () => void;
}) {
  const { workspaceSlug, initiative, isOpen, onClose } = props;
  const { t } = useTranslation();
  const router = useAppRouter();
  const { deleteInitiative } = useInitiative();
  const [isDeleting, setIsDeleting] = useState(false);
  const isGoal = initiative.kind === "goal";

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteInitiative(workspaceSlug, initiative.id);
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t(isGoal ? "initiatives.toast.goal_deleted" : "initiatives.toast.initiative_deleted"),
      });
      onClose();
      router.push(`/${workspaceSlug}/initiatives/`);
    } catch (error) {
      setToast({ type: "error", title: t("toast.error"), message: getInitiativeErrorMessage(error, t) });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <ConfirmDialog
      isOpen={isOpen}
      handleClose={onClose}
      handleSubmit={handleDelete}
      isSubmitting={isDeleting}
      title={t(isGoal ? "initiatives.delete.goal_title" : "initiatives.delete.initiative_title")}
      content={
        <>
          {t(isGoal ? "initiatives.delete.goal_description" : "initiatives.delete.initiative_description", {
            name: initiative.name,
          })}
        </>
      }
    />
  );
});
