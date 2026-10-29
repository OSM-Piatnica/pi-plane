/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { START_OF_THE_WEEK_OPTIONS } from "@plane/constants";
import { Select, SelectDropdownPlacementContext } from "@plane/blocks/select";
import { setToast } from "@plane/blocks/toast";
import type { EStartOfTheWeek } from "@plane/types";
// components
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUserProfile } from "@/hooks/store/user";
import { useCalendarLocale } from "@/hooks/use-calendar-locale";
import { useTranslation } from "@plane/i18n";

// `value: null` is "follow the project (or workspace) setting"
type TStartOfWeekOption = { value: EStartOfTheWeek | null };

const START_OF_WEEK_CHOICES: TStartOfWeekOption[] = [{ value: null }, ...START_OF_THE_WEEK_OPTIONS];
const FOLLOW_PROJECT_KEY = "default";

const getOptionKey = (option: TStartOfWeekOption) =>
  option.value === null ? FOLLOW_PROJECT_KEY : String(option.value);

const getStartOfWeekOption = (startOfWeek: EStartOfTheWeek | null | undefined) =>
  START_OF_WEEK_CHOICES.find((option) => option.value === (startOfWeek ?? null)) ?? null;

// The dropdown opens flush with the control's right edge, as `placement="bottom-end"` did.
const DROPDOWN_PLACEMENT = { side: "bottom", align: "end" } as const;

export const StartOfWeekPreference = observer(function StartOfWeekPreference(props: {
  option: { title: string; description: string };
}) {
  // hooks
  const { t } = useTranslation();
  const { data: userProfile, updateUserProfile } = useUserProfile();
  const { getWeekdayName } = useCalendarLocale();

  const handleStartOfWeekChange = async (val: EStartOfTheWeek | null) => {
    try {
      await updateUserProfile({ start_of_the_week: val });
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("profile_ui.first_day_updated"),
      });
    } catch (_error) {
      setToast({
        type: "error",
        title: t("profile_ui.update_failed"),
        message: t("profile_ui.try_again_later"),
      });
    }
  };

  const getOptionLabel = (option: TStartOfWeekOption) =>
    option.value === null ? t("profile_ui.first_day_project_default") : getWeekdayName(option.value);

  // derived values
  const selectedOption = getStartOfWeekOption(userProfile?.start_of_the_week);

  return (
    <SettingsControlItem
      title={props.option.title}
      description={props.option.description}
      control={
        <SelectDropdownPlacementContext.Provider value={DROPDOWN_PLACEMENT}>
          <Select<TStartOfWeekOption>
            getValues={() => START_OF_WEEK_CHOICES}
            value={selectedOption}
            onChange={(val) =>
              void handleStartOfWeekChange(val === FOLLOW_PROJECT_KEY ? null : (Number(val) as EStartOfTheWeek))
            }
            getOptionValue={getOptionKey}
            getOptionLabel={getOptionLabel}
            showSearch={false}
            pinSelected={false}
            contentSizing="anchor"
          >
            <Select.Trigger<TStartOfWeekOption> variant="select-md" className="w-42 max-w-full border-subtle-1">
              {(options) => (
                <span className="min-w-0 grow truncate text-left">
                  {options[0] ? getOptionLabel(options[0]) : null}
                </span>
              )}
            </Select.Trigger>
          </Select>
        </SelectDropdownPlacementContext.Provider>
      }
    />
  );
});
