/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// hooks
import { useUserProfile } from "@/hooks/store/user";

/**
 * Shown instead of the custom theme editor while the saved theme is an instance theme.
 * "Copy as custom theme" cuts the link to the instance theme and keeps the colours as they are, so the editor opens
 * on exactly what the user was looking at.
 */
export const InstanceThemeNotice = observer(function InstanceThemeNotice() {
  // store hooks
  const { updateUserTheme } = useUserProfile();
  // translation
  const { t } = useTranslation();
  // state
  const [isCopying, setIsCopying] = useState(false);

  const handleCopy = async () => {
    setIsCopying(true);
    try {
      // only the link goes; the colours stay as saved, so nothing changes on screen and no reload is needed
      await updateUserTheme({ instanceThemeId: undefined });
      setToast({ type: "success", title: t("toast.success"), message: t("core_ui.theme.copied_as_custom") });
    } catch (error) {
      console.error("Failed to copy the instance theme:", error);
      setToast({ type: "error", title: t("toast.error"), message: t("core_ui.theme.update_failed") });
    } finally {
      setIsCopying(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-subtle bg-layer-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-body-sm-regular text-secondary">{t("core_ui.theme.instance_managed")}</p>
      <Button
        variant="secondary"
        size="md"
        stretch="auto"
        type="button"
        label={t("core_ui.theme.copy_as_custom")}
        loading={isCopying}
        onClick={() => {
          void handleCopy();
        }}
      />
    </div>
  );
});
