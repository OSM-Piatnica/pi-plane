/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { START_OF_THE_WEEK_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomSelect } from "@plane/ui";
// components
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUserProfile } from "@/hooks/store/user";
import { useCalendarLocale } from "@/hooks/use-calendar-locale";

export const StartOfWeekPreference = observer(function StartOfWeekPreference(props: {
  option: { title: string; description: string };
}) {
  // hooks
  const { t } = useTranslation();
  const { data: userProfile, updateUserProfile } = useUserProfile();
  const { getWeekdayName } = useCalendarLocale();

  const handleStartOfWeekChange = async (val: number) => {
    try {
      await updateUserProfile({ start_of_the_week: val });
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("profile_ui.first_day_updated"),
      });
    } catch (_error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("profile_ui.update_failed"),
        message: t("profile_ui.try_again_later"),
      });
    }
  };

  return (
    <SettingsControlItem
      title={props.option.title}
      description={props.option.description}
      control={
        <CustomSelect
          value={userProfile.start_of_the_week}
          label={getWeekdayName(userProfile.start_of_the_week)}
          onChange={handleStartOfWeekChange}
          buttonClassName="border border-subtle-1"
          input
          maxHeight="lg"
          placement="bottom-end"
        >
          <>
            {START_OF_THE_WEEK_OPTIONS.map((day) => (
              <CustomSelect.Option key={day.value} value={day.value}>
                {getWeekdayName(day.value)}
              </CustomSelect.Option>
            ))}
          </>
        </CustomSelect>
      }
    />
  );
});
