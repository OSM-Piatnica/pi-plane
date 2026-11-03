/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
import { observer } from "mobx-react";
import { useTheme } from "next-themes";
// plane imports
import type { I_THEME_OPTION } from "@plane/constants";
import { THEME_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { setPromiseToast } from "@plane/blocks/toast";
// components
import { CustomThemeSelector } from "@/components/core/theme/custom-theme-selector";
import { ThemeSwitch } from "@/components/core/theme/theme-switch";
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUserProfile } from "@/hooks/store/user";

export const ThemeSwitcher = observer(function ThemeSwitcher(props: {
  option: {
    id: string;
    title: string;
    description: string;
  };
}) {
  // store hooks
  const { data: userProfile, updateUserTheme } = useUserProfile();
  // theme
  const { theme: activeTheme, setTheme } = useTheme();
  // translation
  const { t } = useTranslation();
  // derived values
  // The saved profile theme wins; without one, show the theme the app is already using (e.g. "system").
  const currentTheme = useMemo(() => {
    const themeValue = userProfile?.theme?.theme || activeTheme;
    return THEME_OPTIONS.find((option) => option.value === themeValue) ?? null;
  }, [userProfile?.theme?.theme, activeTheme]);

  const handleThemeChange = useCallback(
    (themeOption: I_THEME_OPTION) => {
      try {
        setTheme(themeOption.value);
        const updatePromise = updateUserTheme({ theme: themeOption.value });
        setPromiseToast(updatePromise, {
          loading: "Updating theme...",
          success: {
            title: t("toast.success"),
            message: () => "Theme updated successfully!",
          },
          error: {
            title: t("toast.error"),
            message: () => "Failed to update the theme",
          },
        });
      } catch (error) {
        console.error("Error updating theme:", error);
      }
    },
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- dependencies intentionally limited
    [updateUserTheme]
  );

  if (!userProfile) return null;

  return (
    <>
      <SettingsControlItem
        title={t(props.option.title)}
        description={t(props.option.description)}
        control={<ThemeSwitch value={currentTheme} onChange={handleThemeChange} />}
      />
      {userProfile.theme?.theme === "custom" && <CustomThemeSelector />}
    </>
  );
});
