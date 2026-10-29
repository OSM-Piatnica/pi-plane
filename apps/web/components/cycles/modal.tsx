/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { mutate } from "swr";
// types
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
import type { CycleDateCheckData, ICycle, TCycleTabOptions } from "@plane/types";
// ui
import { Dialog, DialogContent } from "@makeplane/propel/components/dialog";
// hooks
import { renderFormattedPayloadDate } from "@plane/utils";
import { useCycle } from "@/hooks/store/use-cycle";
import { useProject } from "@/hooks/store/use-project";
import useLocalStorage from "@/hooks/use-local-storage";
import { usePlatformOS } from "@/hooks/use-platform-os";
// services
import { CycleService } from "@/services/cycle.service";
// local imports
import { CycleForm } from "./form";

type CycleModalProps = {
  isOpen: boolean;
  handleClose: () => void;
  data?: ICycle | null;
  workspaceSlug: string;
  projectId: string;
};

// services
const cycleService = new CycleService();

export function CycleCreateUpdateModal(props: CycleModalProps) {
  const { isOpen, handleClose, data, workspaceSlug, projectId } = props;
  // states
  const [activeProject, setActiveProject] = useState<string | null>(null);
  // whether the form holds anything the user entered; an outside click then no longer closes the dialog
  const [hasFormInput, setHasFormInput] = useState(false);
  // store hooks
  const { workspaceProjectIds } = useProject();
  const { createCycle, updateCycleDetails } = useCycle();
  const { isMobile } = usePlatformOS();
  const { t } = useTranslation();

  const { setValue: setCycleTab } = useLocalStorage<TCycleTabOptions>("cycle_tab", "active");

  const handleCreateCycle = async (payload: Partial<ICycle>) => {
    if (!workspaceSlug || !projectId) return;

    const selectedProjectId = payload.project_id ?? projectId.toString();
    await createCycle(workspaceSlug, selectedProjectId, payload)
      .then((_res) => {
        // mutate when the current cycle creation is active
        if (payload.start_date && payload.end_date) {
          const currentDate = new Date();
          const cycleStartDate = new Date(payload.start_date);
          const cycleEndDate = new Date(payload.end_date);
          if (currentDate >= cycleStartDate && currentDate <= cycleEndDate) {
            mutate(`PROJECT_ACTIVE_CYCLE_${selectedProjectId}`);
          }
        }

        setToast({
          type: "success",
          title: t("toast.success"),
          message: t("cycle_ui.create_success"),
        });
        return;
      })
      .catch((err) => {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: err?.detail ?? t("cycle_ui.create_error"),
        });
      });
  };

  const handleUpdateCycle = async (cycleId: string, payload: Partial<ICycle>) => {
    if (!workspaceSlug || !projectId) return;

    const selectedProjectId = payload.project_id ?? projectId.toString();
    await updateCycleDetails(workspaceSlug, selectedProjectId, cycleId, payload)
      .then((_res) => {
        setToast({
          type: "success",
          title: t("toast.success"),
          message: t("project_cycles.action.update.success.description"),
        });
        return;
      })
      .catch((err) => {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: err?.detail ?? t("project_cycles.action.update.failed.description"),
        });
      });
  };

  const dateChecker = async (checkProjectId: string, payload: CycleDateCheckData) => {
    let status = false;

    await cycleService.cycleDateCheck(workspaceSlug, checkProjectId, payload).then((res) => {
      status = res.status;
      return;
    });

    return status;
  };

  const handleFormSubmit = async (formData: Partial<ICycle>) => {
    if (!workspaceSlug || !projectId) return;

    const payload: Partial<ICycle> = {
      ...formData,
      start_date: renderFormattedPayloadDate(formData.start_date) ?? null,
      end_date: renderFormattedPayloadDate(formData.end_date) ?? null,
    };

    let isDateValid: boolean = true;

    if (payload.start_date && payload.end_date) {
      if (data?.id) {
        // Update existing cycle - only check dates if they've changed
        const originalStartDate = renderFormattedPayloadDate(data.start_date) ?? null;
        const originalEndDate = renderFormattedPayloadDate(data.end_date) ?? null;
        const hasDateChanged = payload.start_date !== originalStartDate || payload.end_date !== originalEndDate;

        if (hasDateChanged) {
          isDateValid = await dateChecker(projectId, {
            start_date: payload.start_date,
            end_date: payload.end_date,
            cycle_id: data.id,
          });
        }
      } else {
        // Create new cycle - always check dates
        isDateValid = await dateChecker(projectId, {
          start_date: payload.start_date,
          end_date: payload.end_date,
        });
      }
    }

    if (isDateValid) {
      if (data?.id) await handleUpdateCycle(data.id, payload);
      else {
        await handleCreateCycle(payload).then(() => {
          setCycleTab("all");
          return;
        });
      }
      handleClose();
    } else
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("project_cycles.action.update.error.already_exists"),
      });
  };

  // react-doctor-disable-next-line no-derived-state-effect -- activeProject is also written by the form's project selector, so it is not a pure function of props
  useEffect(() => {
    // if modal is closed, reset active project to null
    // and return to avoid activeProject being set to some other project
    if (!isOpen) {
      // react-doctor-disable-next-line no-adjust-state-on-prop-change -- activeProject is also set by the form's project selector, so it is not a pure function of props
      setActiveProject(null);
      return;
    }

    // if data is present, set active project to the project of the
    // issue. This has more priority than the project in the url.
    if (data && data.project_id) {
      // react-doctor-disable-next-line no-derived-state -- activeProject is also written by CycleForm via setActiveProject, so it is user-editable state seeded from props
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
      // An outside press or Escape closes the untouched form; once the user has entered something, propel asks
      // before discarding it. The form's own Cancel button closes without asking.
      discard={{
        when: hasFormInput,
        title: t("discard_changes.title"),
        description: t("discard_changes.description"),
        discardLabel: t("discard"),
        keepLabel: t("discard_changes.keep_editing"),
      }}
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogContent size="md">
        {/* the form has no DialogBody scroller of its own, so this keeps it reachable on short windows */}
        <div className="vertical-scrollbar scrollbar-sm min-h-0 flex-1 overflow-y-auto">
          <CycleForm
            handleFormSubmit={handleFormSubmit}
            handleClose={handleClose}
            onInputChange={setHasFormInput}
            status={!!data}
            projectId={activeProject ?? ""}
            setActiveProject={setActiveProject}
            data={data}
            isMobile={isMobile}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
