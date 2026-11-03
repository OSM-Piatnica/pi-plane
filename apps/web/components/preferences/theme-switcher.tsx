/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
import { observer } from "mobx-react";
import { useTheme } from "next-themes";
import useSWR from "swr";
// plane imports
import { THEME_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { setPromiseToast } from "@plane/blocks/toast";
import { InstanceService } from "@plane/services";
import type { TInstanceTheme } from "@plane/types";
import { applyCustomTheme, sanitizeThemeOverrides } from "@plane/utils";
// components
import { CustomThemeSelector } from "@/components/core/theme/custom-theme-selector";
import { ThemeSwitch } from "@/components/core/theme/theme-switch";
import type { TThemeSwitchOption } from "@/components/core/theme/theme-switch";
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUserProfile } from "@/hooks/store/user";

const instanceService = new InstanceService();
const INSTANCE_THEME_PREFIX = "instance:";

// An instance theme in the list: its colours stand in for the icon of the built-in themes
const toThemeOption = (theme: TInstanceTheme): TThemeSwitchOption => ({
  key: theme.name,
  label: theme.name,
  value: `${INSTANCE_THEME_PREFIX}${theme.id}`,
  i18n_label: theme.name,
  type: theme.dark_palette ? "dark" : "light",
  icon: { border: theme.dark_palette ? "#2E3234" : "#DEE2E6", color1: theme.background, color2: theme.primary },
});

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
  const { data: instanceThemes } = useSWR("INSTANCE_THEMES", () => instanceService.themes());
  // derived values
  const instanceThemeOptions = useMemo(() => (instanceThemes ?? []).map(toThemeOption), [instanceThemes]);
  const currentTheme = useMemo(() => {
    // An instance theme is saved as a custom theme that remembers where it came from
    const instanceThemeId = userProfile?.theme?.instanceThemeId;
    if (userProfile?.theme?.theme === "custom" && instanceThemeId) {
      const instanceOption = instanceThemeOptions.find(
        (option) => option.value === `${INSTANCE_THEME_PREFIX}${instanceThemeId}`
      );
      if (instanceOption) return instanceOption;
    }
    // The saved profile theme wins; without one, show the theme the app is already using (e.g. "system").
    const themeValue = userProfile?.theme?.theme || activeTheme;
    return THEME_OPTIONS.find((themeItem) => themeItem.value === themeValue) ?? null;
  }, [userProfile?.theme?.theme, userProfile?.theme?.instanceThemeId, instanceThemeOptions, activeTheme]);

  const handleThemeChange = useCallback(
    async (themeOption: TThemeSwitchOption) => {
      try {
        // An instance theme becomes the user's custom theme, with the colours the admin chose
        const instanceTheme = themeOption.value.startsWith(INSTANCE_THEME_PREFIX)
          ? instanceThemes?.find((theme) => `${INSTANCE_THEME_PREFIX}${theme.id}` === themeOption.value)
          : undefined;
        if (instanceTheme) {
          const overrides = sanitizeThemeOverrides(instanceTheme.overrides).overrides;
          setTheme("custom");
          applyCustomTheme(
            instanceTheme.primary,
            instanceTheme.background,
            instanceTheme.dark_palette ? "dark" : "light",
            overrides
          );
          const updatePromise = updateUserTheme({
            theme: "custom",
            primary: instanceTheme.primary,
            background: instanceTheme.background,
            darkPalette: instanceTheme.dark_palette,
            overrides,
            instanceThemeId: instanceTheme.id,
          });
          setPromiseToast(updatePromise, {
            loading: t("core_ui.theme.updating"),
            success: { title: t("core_ui.theme.updated"), message: () => t("core_ui.theme.reloading") },
            error: { title: t("toast.error"), message: () => t("core_ui.theme.update_failed") },
          });
          await updatePromise;
          window.location.reload();
          return;
        }

        setTheme(themeOption.value);

        // If switching to custom theme and user has saved custom colors, apply them immediately
        if (
          themeOption.value === "custom" &&
          userProfile?.theme?.primary &&
          userProfile?.theme?.background &&
          userProfile?.theme?.darkPalette !== undefined
        ) {
          applyCustomTheme(
            userProfile.theme.primary,
            userProfile.theme.background,
            userProfile.theme.darkPalette ? "dark" : "light",
            userProfile.theme.overrides
          );
        }

        const updatePromise = updateUserTheme({ theme: themeOption.value, instanceThemeId: undefined });
        setPromiseToast(updatePromise, {
          loading: t("core_ui.theme.updating"),
          success: {
            title: t("core_ui.theme.updated"),
            message: () => t("core_ui.theme.reloading"),
          },
          error: {
            title: t("toast.error"),
            message: () => t("core_ui.theme.update_failed"),
          },
        });
        // Wait for the promise to resolve, then reload after showing toast
        await updatePromise;
        window.location.reload();
      } catch (error) {
        console.error("Error updating theme:", error);
      }
    },
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- intentionally limited deps; behaviour unchanged
    [setTheme, updateUserTheme, userProfile, instanceThemes]
  );

  if (!userProfile) return null;

  return (
    <>
      <SettingsControlItem
        title={t(props.option.title)}
        description={t(props.option.description)}
        control={
          <ThemeSwitch
            value={currentTheme}
            extraOptions={instanceThemeOptions}
            onChange={(themeOption) => {
              void handleThemeChange(themeOption);
            }}
          />
        }
      />
      {userProfile.theme?.theme === "custom" && <CustomThemeSelector />}
    </>
  );
});
