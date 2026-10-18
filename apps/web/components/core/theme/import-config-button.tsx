/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useRef } from "react";
import { observer } from "mobx-react";
import type { UseFormSetValue } from "react-hook-form";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import type { IUserTheme } from "@plane/types";

type Props = {
  handleUpdateTheme: (formData: IUserTheme) => Promise<void>;
  setValue: UseFormSetValue<IUserTheme>;
};

export const CustomThemeImportConfigButton = observer(function CustomThemeImportConfigButton(props: Props) {
  const { handleUpdateTheme, setValue } = props;
  // refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  // translation
  const { t } = useTranslation();

  const handleUploadConfig = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const config = JSON.parse(text) as IUserTheme;

      // Validate required fields
      if (!config.primary || !config.background) {
        throw new Error(t("app_text.theme.missing_fields"));
      }

      // Validate hex color format
      const hexPattern = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
      if (!hexPattern.test(config.primary)) {
        throw new Error(t("app_text.theme.invalid_brand_hex"));
      }
      if (!hexPattern.test(config.background)) {
        throw new Error(t("app_text.theme.invalid_neutral_hex"));
      }

      // Validate theme mode
      const themeMode = config.darkPalette ?? false;
      if (typeof themeMode !== "boolean") {
        throw new Error(t("app_text.theme.invalid_mode"));
      }

      // Apply the configuration to form
      const formData: IUserTheme = {
        theme: "custom",
        primary: config.primary,
        background: config.background,
        darkPalette: themeMode,
      };

      // Update form values
      setValue("primary", formData.primary);
      setValue("background", formData.background);
      setValue("darkPalette", formData.darkPalette);
      setValue("theme", "custom");

      // Apply the theme
      await handleUpdateTheme(formData);

      setToast({
        type: "success",
        title: t("success"),
        message: t("core_ui.theme.import_success"),
      });
    } catch (error) {
      console.error("Failed to upload config:", error);
      setToast({
        type: "error",
        title: t("error"),
        message: error instanceof Error ? error.message : t("app_text.theme.import_failed"),
      });
    } finally {
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <>
      <input ref={fileInputRef} type="file" accept=".json" onChange={handleUploadConfig} className="hidden" />
      <Button
        variant="secondary"
        size="md"
        stretch="auto"
        type="button"
        label={t("app_text.theme.import_config")}
        onClick={() => fileInputRef.current?.click()}
      />
    </>
  );
});
