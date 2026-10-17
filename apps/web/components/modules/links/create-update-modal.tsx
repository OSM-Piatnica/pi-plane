/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
// plane types
import { Field } from "@makeplane/propel/components/field";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { ILinkDetails, ModuleLink } from "@plane/types";
// plane ui
import { ModalCore } from "@plane/ui";
import { useTranslation } from "@plane/i18n";
type Props = {
  createLink: (formData: ModuleLink) => Promise<void>;
  data?: ILinkDetails | null;
  isOpen: boolean;
  handleClose: () => void;
  updateLink: (formData: ModuleLink, linkId: string) => Promise<void>;
};

const defaultValues: ModuleLink = {
  title: "",
  url: "",
};

export function CreateUpdateModuleLinkModal(props: Props) {
  const { isOpen, handleClose, createLink, updateLink, data } = props;
  const { t } = useTranslation();
  // form info
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    control,
    reset,
  } = useForm<ModuleLink>({
    defaultValues,
  });

  const onClose = () => {
    handleClose();
  };

  const handleFormSubmit = async (formData: ModuleLink) => {
    const parsedUrl = formData.url.startsWith("http") ? formData.url : `http://${formData.url}`;
    const payload = {
      title: formData.title,
      url: parsedUrl,
    };

    try {
      if (!data) {
        await createLink(payload);
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: t("toast.success"),
          message: t("links.toasts.created.message"),
        });
      } else {
        await updateLink(payload, data.id);
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: t("toast.success"),
          message: t("links.toasts.updated.message"),
        });
      }
      onClose();
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: error?.data?.error ?? t("common.error.message"),
      });
    }
  };

  useEffect(() => {
    reset({
      ...defaultValues,
      ...data,
    });
  }, [data, isOpen, reset]);

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose}>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <div className="space-y-5 p-5">
          <h3 className="text-18 font-medium text-secondary">
            {data ? t("common.update_link") : t("common.add_link")}
          </h3>
          <div className="mt-2 space-y-3">
            <div>
              <label htmlFor="url" className="mb-2 text-secondary">
                URL
              </label>
              <Controller
                control={control}
                name="url"
                rules={{
                  required: "URL is required",
                }}
                render={({ field: { value, onChange, ref } }) => (
                  <Field name="url" invalid={Boolean(errors.url)}>
                    <InputGroup size="2xl">
                      <Input
                        size="2xl"
                        id="url"
                        type="text"
                        value={value}
                        onChange={onChange}
                        ref={ref}
                        placeholder={t("module_ui.url_placeholder")}
                      />
                    </InputGroup>
                  </Field>
                )}
              />
            </div>
            <div>
              <label htmlFor="title" className="mb-2 text-secondary">
                Display title
                <span className="block text-10">{t("common.optional")}</span>
              </label>
              <Controller
                control={control}
                name="title"
                render={({ field: { value, onChange, ref } }) => (
                  <Field name="title" invalid={Boolean(errors.title)}>
                    <InputGroup size="2xl">
                      <Input
                        size="2xl"
                        id="title"
                        type="text"
                        value={value}
                        onChange={onChange}
                        ref={ref}
                        placeholder={t("module_ui.link_title_placeholder")}
                      />
                    </InputGroup>
                  </Field>
                )}
              />
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t-[0.5px] border-subtle px-5 py-4">
          <Button variant="secondary" size="lg" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" size="lg" type="submit" loading={isSubmitting}>
            {data
              ? isSubmitting
                ? t("module_ui.updating_link")
                : t("common.update_link")
              : isSubmitting
                ? t("module_ui.adding_link")
                : t("common.add_link")}
          </Button>
        </div>
      </form>
    </ModalCore>
  );
}
