/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useForm } from "react-hook-form";
// Plane imports
import { Dialog, DialogContent } from "@makeplane/propel/components/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { IModule } from "@plane/types";
// components
import { ModuleForm } from "@/components/modules";
// hooks
import { useModule } from "@/hooks/store/use-module";
import { useProject } from "@/hooks/store/use-project";
import { usePlatformOS } from "@/hooks/use-platform-os";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  data?: IModule;
  workspaceSlug: string;
  projectId: string;
};

const defaultValues: Partial<IModule> = {
  name: "",
  description: "",
  status: "backlog",
  lead_id: null,
  member_ids: [],
};

export const CreateUpdateModuleModal = observer(function CreateUpdateModuleModal(props: Props) {
  const { isOpen, onClose, data, workspaceSlug, projectId } = props;
  // states
  const [activeProject, setActiveProject] = useState<string | null>(null);
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { workspaceProjectIds } = useProject();
  const { createModule, updateModuleDetails } = useModule();
  const { isMobile } = usePlatformOS();

  const handleClose = () => {
    reset(defaultValues);
    onClose();
  };

  const { reset } = useForm<IModule>({
    defaultValues,
  });

  const handleCreateModule = async (payload: Partial<IModule>) => {
    if (!workspaceSlug || !projectId) return;

    const selectedProjectId = payload.project_id ?? projectId.toString();
    await createModule(workspaceSlug.toString(), selectedProjectId, payload)
      .then((_res) => {
        handleClose();
        setToast({
          type: "success",
          title: t("toast.success"),
          message: t("module_ui.create_success"),
        });
        return;
      })
      .catch((err) => {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: err?.detail ?? err?.error ?? t("module_ui.create_error"),
        });
      });
  };

  const handleUpdateModule = async (payload: Partial<IModule>) => {
    if (!workspaceSlug || !projectId || !data) return;

    const selectedProjectId = payload.project_id ?? projectId.toString();
    await updateModuleDetails(workspaceSlug.toString(), selectedProjectId, data.id, payload)
      .then((_res) => {
        handleClose();

        setToast({
          type: "success",
          title: t("toast.success"),
          message: t("entity.update.success", { entity: t("common.module") }),
        });
        return;
      })
      .catch((err) => {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: err?.detail ?? err?.error ?? t("module_ui.update_error"),
        });
      });
  };

  const handleFormSubmit = async (formData: Partial<IModule>) => {
    if (!workspaceSlug || !projectId) return;

    const payload: Partial<IModule> = {
      ...formData,
    };
    if (!data) await handleCreateModule(payload);
    else await handleUpdateModule(payload);
  };

  // react-doctor-disable-next-line no-derived-state-effect -- activeProject is also written by the form's project selector, so it is not a pure function of props
  useEffect(() => {
    // if modal is closed, reset active project to null
    // and return to avoid activeProject being set to some other project
    if (!isOpen) {
      // react-doctor-disable-next-line no-adjust-state-on-prop-change -- reset to null on close is part of the priority logic in this effect, which also depends on activeProject
      setActiveProject(null);
      return;
    }

    // if data is present, set active project to the project of the
    // issue. This has more priority than the project in the url.
    if (data && data.project_id) {
      // react-doctor-disable-next-line no-adjust-state-on-prop-change, no-derived-state -- activeProject also reads itself and the url/workspace project list; effect resolves priority between several inputs
      setActiveProject(data.project_id);
      return;
    }

    // if data is not present, set active project to the project
    // in the url. This has the least priority.
    if (workspaceProjectIds && workspaceProjectIds.length > 0 && !activeProject)
      setActiveProject(projectId ?? workspaceProjectIds?.[0] ?? null);
  }, [activeProject, data, projectId, workspaceProjectIds, isOpen]);

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
      disablePointerDismissal
    >
      {/* ModuleForm renders its own visible heading; the dialog carries the same text as its name. */}
      <DialogContent
        size="md"
        aria-label={`${data ? t("common.update") : t("common.create")} ${t("common.module").toLowerCase()}`}
      >
        <ModuleForm
          handleFormSubmit={handleFormSubmit}
          handleClose={handleClose}
          status={!!data}
          projectId={activeProject ?? ""}
          setActiveProject={setActiveProject}
          data={data}
          isMobile={isMobile}
        />
      </DialogContent>
    </Dialog>
  );
});
