/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
// components
import { WeekendDaysSelect } from "@/components/global/weekend-days-select";
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUserProfile } from "@/hooks/store/user";
import { useWeekendDays } from "@/hooks/use-weekend-days";

/**
 * The person's own non-working days. They apply where no project decides (My work, workspace views, date pickers):
 * inside a project the project's days are used, so durations and shading agree for everyone. Until the person picks
 * days, they follow the workspace.
 */
export const WeekendDaysPreference = observer(function WeekendDaysPreference() {
  // hooks
  const { t } = useTranslation();
  const { data: userProfile, updateUserProfile } = useUserProfile();
  const weekendDays = useWeekendDays();
  // derived values
  const hasOwnChoice = userProfile?.weekend_days !== null && userProfile?.weekend_days !== undefined;

  const handleChange = async (days: number[] | null) => {
    try {
      await updateUserProfile({ weekend_days: days });
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("project_components.profile.weekend_days_updated"),
      });
    } catch (_error) {
      setToast({
        type: "error",
        title: t("profile_ui.update_failed"),
        message: t("profile_ui.try_again_later"),
      });
    }
  };

  return (
    <SettingsControlItem
      title={t("project_components.profile.weekend_days")}
      description={t("project_components.profile.weekend_days_description")}
      control={
        <div className="flex w-42 max-w-full flex-col items-end gap-1">
          <WeekendDaysSelect value={weekendDays} onChange={(days) => void handleChange(days)} />
          {hasOwnChoice && (
            <button
              type="button"
              className="text-12 text-accent-primary hover:underline"
              onClick={() => void handleChange(null)}
            >
              {t("project_components.profile.weekend_days_use_default")}
            </button>
          )}
        </div>
      }
    />
  );
});
