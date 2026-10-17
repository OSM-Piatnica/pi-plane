/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// ui
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
// hooks
import { useProjectEstimates } from "@/hooks/store/estimates";
import { useEstimate } from "@/hooks/store/estimates/use-estimate";
import { useProject } from "@/hooks/store/use-project";

type TDeleteEstimateModal = {
  workspaceSlug: string;
  projectId: string;
  estimateId: string | undefined;
  isOpen: boolean;
  handleClose: () => void;
};

export const DeleteEstimateModal = observer(function DeleteEstimateModal(props: TDeleteEstimateModal) {
  // props
  const { workspaceSlug, projectId, estimateId, isOpen, handleClose } = props;
  // hooks
  const { areEstimateEnabledByProjectId, deleteEstimate } = useProjectEstimates();
  const { asJson: estimate } = useEstimate(estimateId);
  const { updateProject } = useProject();
  const { t } = useTranslation();
  // states
  const [buttonLoader, setButtonLoader] = useState(false);

  const handleDeleteEstimate = async () => {
    try {
      if (!workspaceSlug || !projectId || !estimateId) return;
      setButtonLoader(true);
      await deleteEstimate(workspaceSlug, projectId, estimateId);
      if (areEstimateEnabledByProjectId(projectId)) {
        await updateProject(workspaceSlug, projectId, { estimate: null });
      }
      setButtonLoader(false);
      setToast({
        type: "success",
        title: t("core_ui.estimate.deleted_title"),
        message: t("core_ui.estimate.deleted_message"),
      });
      handleClose();
    } catch (_error) {
      setButtonLoader(false);
      setToast({
        type: "error",
        title: t("core_ui.estimate.delete_failed_title"),
        message: t("core_ui.estimate.delete_failed_message"),
      });
    }
  };

  return (
    <Dialog
      open={isOpen}
      disablePointerDismissal
      onOpenChange={(open, eventDetails) => {
        if (open) return;
        // The legacy modal took no `handleClose`, so Escape was swallowed: only Cancel closed it.
        if (eventDetails.reason === "escape-key") return;
        handleClose();
      }}
    >
      <DialogContent size="md">
        <DialogMain>
          {/* heading */}
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>Delete Estimate System</DialogTitle>
            </DialogHeading>
          </DialogHeader>

          {/* estimate steps */}
          <DialogBody tabIndex={0}>
            <div className="text-14 text-secondary">
              Deleting the estimate <span className="font-bold text-primary">{estimate?.name}</span>
              &nbsp;system will remove it from all work items permanently. This action cannot be undone. If you add
              estimates again, you will need to update all the work items.
            </div>
          </DialogBody>
        </DialogMain>

        <DialogActions>
          <Button
            variant="secondary"
            size="md"
            onClick={handleClose}
            disabled={buttonLoader}
            stretch="auto"
            label="Cancel"
          />
          <Button
            variant="danger"
            size="md"
            onClick={handleDeleteEstimate}
            disabled={buttonLoader}
            stretch="auto"
            label={buttonLoader ? "Deleting" : "Delete Estimate"}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
});
