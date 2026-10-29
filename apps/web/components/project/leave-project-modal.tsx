/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { WarningTriangleOutline } from "@makeplane/propel/icons";
// Plane imports
import { Field } from "@makeplane/propel/components/field";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import type { IProject } from "@plane/types";
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
import { useUserPermissions } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { useTranslation } from "@plane/i18n";

type FormData = {
  projectName: string;
  confirmLeave: string;
};

const defaultValues: FormData = {
  projectName: "",
  confirmLeave: "",
};

export interface ILeaveProjectModal {
  project: IProject;
  isOpen: boolean;
  onClose: () => void;
}

export const LeaveProjectModal = observer(function LeaveProjectModal(props: ILeaveProjectModal) {
  const { project, isOpen, onClose } = props;
  // translation
  const { t } = useTranslation();
  // router
  const router = useAppRouter();
  const { workspaceSlug } = useParams();
  // store hooks
  const { leaveProject } = useUserPermissions();

  const {
    control,
    formState: { errors, isSubmitting },
    handleSubmit,
    reset,
  } = useForm({ defaultValues });

  const handleClose = () => {
    reset({ ...defaultValues });
    onClose();
  };

  const onSubmit = async (data: any) => {
    if (!workspaceSlug) return;

    if (data) {
      if (data.projectName === project?.name) {
        if (data.confirmLeave === "Leave Project") {
          return leaveProject(workspaceSlug.toString(), project.id)
            .then(() => {
              handleClose();
              router.push(`/${workspaceSlug}/projects`);
              return;
            })
            .catch((err) => {
              // the API refuses when the user is the project's only admin (every member can now open this dialog)
              const isOnlyAdmin = typeof err?.error === "string" && err.error.includes("only admin");
              setToast({
                type: "error",
                title: t("toast.error"),
                message: isOnlyAdmin
                  ? t("project_components.leave_modal.only_admin_error")
                  : t("something_went_wrong_please_try_again"),
              });
            });
        } else {
          setToast({
            type: "error",
            title: t("toast.error"),
            message: t("project_components.leave_modal.confirm_phrase_error", { phrase: "Leave Project" }),
          });
        }
      } else {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: t("project_components.leave_modal.project_name_error"),
        });
      }
    } else {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("project_components.leave_modal.fill_all_fields"),
      });
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogContent size="md">
        <form onSubmit={handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
          <DialogMain>
            <DialogHeader>
              <div className="flex w-full items-center justify-start gap-6">
                <span className="place-items-center rounded-full bg-danger-subtle p-4">
                  <WarningTriangleOutline className="h-6 w-6 text-danger-primary" aria-hidden="true" />
                </span>
                <DialogHeading>
                  <DialogTitle>{t("project_components.leave_modal.title")}</DialogTitle>
                </DialogHeading>
              </div>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-6">
                <p className="text-13 leading-7 text-secondary">
                  {t("project_components.leave_modal.description", { name: project?.name })}
                </p>
                <div className="text-secondary">
                  <p className="text-13 break-words">
                    {t("project_components.delete_modal.enter_project_name", { name: project?.name })}
                  </p>
                  <Controller
                    control={control}
                    name="projectName"
                    rules={{
                      required: t("project_components.leave_modal.project_name_required"),
                    }}
                    render={({ field: { value, onChange, ref } }) => (
                      <Field name="projectName" invalid={Boolean(errors.projectName)}>
                        <InputGroup size="2xl">
                          <Input
                            size="2xl"
                            id="projectName"
                            name="projectName"
                            type="text"
                            value={value}
                            onChange={onChange}
                            ref={ref}
                            placeholder={t("project_components.leave_modal.project_name_placeholder")}
                          />
                        </InputGroup>
                      </Field>
                    )}
                  />
                </div>
                <div className="text-secondary">
                  <p className="text-13">
                    {t("project_components.delete_modal.confirm_type", { phrase: "Leave Project" })}
                  </p>
                  <Controller
                    control={control}
                    name="confirmLeave"
                    render={({ field: { value, onChange, ref } }) => (
                      <Field name="confirmLeave" invalid={Boolean(errors.confirmLeave)}>
                        <InputGroup size="2xl">
                          <Input
                            size="2xl"
                            id="confirmLeave"
                            name="confirmLeave"
                            type="text"
                            value={value}
                            onChange={onChange}
                            ref={ref}
                            placeholder={t("project_components.delete_modal.confirm_placeholder", {
                              phrase: "leave project",
                            })}
                          />
                        </InputGroup>
                      </Field>
                    )}
                  />
                </div>
              </div>
            </DialogBody>
          </DialogMain>
          <DialogActions>
            <Button variant="secondary" size="md" stretch="auto" label={t("cancel")} onClick={handleClose} />
            <Button
              variant="danger"
              size="md"
              stretch="auto"
              type="submit"
              label={isSubmitting ? t("project_components.shared.leaving") : t("project_components.leave_modal.title")}
              loading={isSubmitting}
            />
          </DialogActions>
        </form>
      </DialogContent>
    </Dialog>
  );
});
