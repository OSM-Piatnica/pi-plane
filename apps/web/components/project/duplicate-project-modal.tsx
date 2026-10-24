/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the project duplication of Hangar (szymczag/hangar, AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { CopyPlus } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Checkbox } from "@makeplane/propel/components/checkbox";
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
import { Field } from "@makeplane/propel/components/field";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { setToast } from "@plane/blocks/toast";
import type { IProject } from "@plane/types";
import { projectIdentifierSanitizer } from "@plane/utils";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useAppRouter } from "@/hooks/use-app-router";

type TDuplicateProjectModalProps = {
  isOpen: boolean;
  // Only what the form seeds from, so a partial project works here as well as the full record.
  project: Pick<IProject, "id" | "name" | "identifier">;
  onClose: () => void;
};

type TFormValues = {
  name: string;
  identifier: string;
  labels: boolean;
  estimates: boolean;
  intake: boolean;
  members: boolean;
  cycles: boolean;
  modules: boolean;
  views: boolean;
};

/**
 * Options the API also defaults on. Anything that grants access or carries
 * someone else's work stays off until it is asked for.
 */
const OPTIONAL_COPY_FIELDS = [
  { key: "labels", labelKey: "labels" },
  { key: "estimates", labelKey: "common.estimates" },
  { key: "intake", labelKey: "intake" },
  { key: "members", labelKey: "members" },
  { key: "cycles", labelKey: "cycles" },
  { key: "modules", labelKey: "modules" },
  { key: "views", labelKey: "views" },
] as const;

export function DuplicateProjectModal(props: TDuplicateProjectModalProps) {
  const { isOpen, project, onClose } = props;
  // store hooks
  const { duplicateProject } = useProject();
  // router
  const router = useAppRouter();
  const { workspaceSlug } = useParams();
  // translation
  const { t } = useTranslation();
  // form info
  const {
    control,
    formState: { errors, isSubmitting },
    handleSubmit,
    reset,
    setError,
  } = useForm<TFormValues>();

  // Seed from the source every time the modal opens, so reopening it after a
  // failed submit does not keep a stale name the API already rejected.
  useEffect(() => {
    if (!isOpen) return;
    reset({
      name: `${project.name} (Copy)`,
      // empty: the API derives a free one, whereas the source's own identifier is always taken
      identifier: "",
      labels: true,
      estimates: true,
      intake: true,
      members: false,
      cycles: false,
      modules: false,
      views: false,
    });
  }, [isOpen, project.name, project.identifier, reset]);

  const onSubmit = async (values: TFormValues) => {
    if (!workspaceSlug) return;

    try {
      const copy = await duplicateProject(workspaceSlug.toString(), project.id, {
        name: values.name.trim(),
        ...(values.identifier.trim() ? { identifier: values.identifier.trim().toUpperCase() } : {}),
        include: {
          labels: values.labels,
          estimates: values.estimates,
          intake: values.intake,
          members: values.members,
          cycles: values.cycles,
          modules: values.modules,
          views: values.views,
        },
      });

      onClose();
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("project_components.duplicate_modal.success"),
      });
      router.push(`/${workspaceSlug}/projects/${copy.id}/issues`);
    } catch (error) {
      // The endpoint answers in two shapes: the copy service raises `{ error: CODE }`, while a
      // serializer rejection is DRF's field map, `{ name: [CODE] }`.
      const body = (error as { data?: Record<string, unknown> })?.data ?? {};
      const fieldCodes = (field: string): string[] => {
        const value = body[field];
        return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
      };
      const code = typeof body.error === "string" ? body.error : undefined;
      const has = (field: string, wanted: string) => code === wanted || fieldCodes(field).includes(wanted);

      if (has("name", "PROJECT_NAME_ALREADY_EXIST")) {
        setError("name", { message: t("project_name_already_taken") });
        return;
      }
      if (has("identifier", "PROJECT_IDENTIFIER_ALREADY_EXIST")) {
        setError("identifier", { message: t("project_identifier_already_taken") });
        return;
      }
      if (has("name", "PROJECT_NAME_CANNOT_CONTAIN_SPECIAL_CHARACTERS")) {
        setError("name", { message: t("project_name_cannot_contain_special_characters") });
        return;
      }
      setToast({
        type: "error",
        title: t("toast.error"),
        message:
          code === "PROJECT_TOO_LARGE_TO_COPY_SYNCHRONOUSLY"
            ? t("project_components.duplicate_modal.too_large")
            : t("project_components.duplicate_modal.error"),
      });
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="lg">
        <form onSubmit={handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
          <DialogMain>
            <DialogHeader>
              <div className="flex w-full items-center justify-start gap-6">
                <span className="place-items-center rounded-full bg-layer-1 p-4">
                  <CopyPlus className="h-6 w-6 text-secondary" aria-hidden="true" />
                </span>
                <DialogHeading>
                  <DialogTitle>{t("project_components.duplicate_modal.title")}</DialogTitle>
                </DialogHeading>
              </div>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-6">
                <p className="text-13 leading-6 text-secondary">
                  {t("project_components.duplicate_modal.description")}
                </p>

                <div className="flex gap-4">
                  <div className="flex-grow">
                    <label htmlFor="duplicate-project-name" className="text-13 text-secondary">
                      {t("project_name")}
                    </label>
                    <Controller
                      control={control}
                      name="name"
                      rules={{ required: true, maxLength: 255 }}
                      render={({ field: { value, onChange, ref } }) => (
                        <Field name="name" invalid={Boolean(errors.name)}>
                          <InputGroup size="2xl">
                            <Input
                              size="2xl"
                              id="duplicate-project-name"
                              name="name"
                              type="text"
                              value={value ?? ""}
                              onChange={onChange}
                              ref={ref}
                              autoComplete="off"
                            />
                          </InputGroup>
                        </Field>
                      )}
                    />
                    {errors.name?.message && <p className="mt-1 text-11 text-danger-primary">{errors.name.message}</p>}
                  </div>

                  <div className="w-40 flex-shrink-0">
                    <label htmlFor="duplicate-project-identifier" className="text-13 text-secondary">
                      {t("project_id")}
                    </label>
                    <Controller
                      control={control}
                      name="identifier"
                      rules={{ maxLength: 12 }}
                      render={({ field: { value, onChange, ref } }) => (
                        <Field name="identifier" invalid={Boolean(errors.identifier)}>
                          <InputGroup size="2xl">
                            <Input
                              size="2xl"
                              id="duplicate-project-identifier"
                              name="identifier"
                              type="text"
                              value={value ?? ""}
                              // Mirrors the create form: uppercase, no separators, capped.
                              onChange={(event) =>
                                onChange(projectIdentifierSanitizer(event.target.value.toUpperCase()).slice(0, 12))
                              }
                              ref={ref}
                              placeholder={t("project_components.duplicate_modal.identifier_placeholder")}
                              autoComplete="off"
                            />
                          </InputGroup>
                        </Field>
                      )}
                    />
                    {errors.identifier?.message && (
                      <p className="mt-1 text-11 text-danger-primary">{errors.identifier.message}</p>
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-13 font-medium text-primary">
                    {t("project_components.duplicate_modal.what_to_copy")}
                  </p>
                  <p className="mt-1 text-11 text-secondary">{t("project_components.duplicate_modal.always_copied")}</p>
                  <div className="mt-3 grid grid-cols-2 gap-y-2.5">
                    {OPTIONAL_COPY_FIELDS.map((option) => (
                      <Controller
                        key={option.key}
                        control={control}
                        name={option.key}
                        render={({ field: { value, onChange } }) => (
                          <label className="flex cursor-pointer items-center gap-2 text-13 text-secondary">
                            <Checkbox
                              checked={Boolean(value)}
                              onCheckedChange={(checked) => onChange(checked === true)}
                            />
                            <span>{t(option.labelKey)}</span>
                          </label>
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </DialogBody>
          </DialogMain>
          <DialogActions>
            <Button variant="secondary" size="md" stretch="auto" label={t("cancel")} onClick={onClose} />
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              type="submit"
              label={
                isSubmitting
                  ? t("project_components.duplicate_modal.submitting")
                  : t("project_components.duplicate_modal.submit")
              }
              loading={isSubmitting}
            />
          </DialogActions>
        </form>
      </DialogContent>
    </Dialog>
  );
}
