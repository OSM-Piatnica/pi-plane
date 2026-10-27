/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Select } from "@plane/blocks/select";
import { setToast } from "@plane/blocks/toast";
import type { IUserEmailNotificationSettings, TEmailNotificationFrequency } from "@plane/types";
import { Switch } from "@makeplane/propel/components/switch";
// components
import { SettingsControlItem } from "@/components/settings/control-item";
// services
import { UserService } from "@/services/user.service";

const EMAIL_FREQUENCY_OPTIONS: { value: TEmailNotificationFrequency; i18n_label: string }[] = [
  { value: "instant", i18n_label: "email_frequency_instant" },
  { value: "hourly", i18n_label: "email_frequency_hourly" },
  { value: "daily", i18n_label: "email_frequency_daily" },
];

type Props = {
  data: IUserEmailNotificationSettings;
};

// services
const userService = new UserService();

export const NotificationsProfileSettingsForm = observer(function NotificationsProfileSettingsForm(props: Props) {
  const { data } = props;
  // translation
  const { t } = useTranslation();
  // form data
  const { control, reset } = useForm<IUserEmailNotificationSettings>({
    defaultValues: {
      ...data,
    },
  });

  const handleSettingChange = async (
    key: keyof IUserEmailNotificationSettings,
    value: boolean | TEmailNotificationFrequency
  ) => {
    try {
      await userService.updateCurrentUserEmailNotificationSettings({
        [key]: value,
      });
      setToast({
        title: t("success"),
        type: "success",
        message: t("email_notification_setting_updated_successfully"),
      });
    } catch (_error) {
      setToast({
        title: t("error"),
        type: "error",
        message: t("failed_to_update_email_notification_setting"),
      });
    }
  };

  useEffect(() => {
    reset(data);
  }, [reset, data]);

  return (
    <div className="flex flex-col gap-y-1">
      <SettingsControlItem
        title={t("email_frequency")}
        description={t("email_frequency_description")}
        control={
          <Controller
            control={control}
            name="email_frequency"
            render={({ field: { value, onChange } }) => {
              const selectedOption = EMAIL_FREQUENCY_OPTIONS.find((option) => option.value === value) ?? null;
              return (
                <Select<(typeof EMAIL_FREQUENCY_OPTIONS)[number]>
                  getValues={() => EMAIL_FREQUENCY_OPTIONS}
                  value={selectedOption}
                  onChange={(newValue) => {
                    onChange(newValue);
                    void handleSettingChange("email_frequency", newValue as TEmailNotificationFrequency);
                  }}
                  getOptionValue={(option) => option.value}
                  getOptionLabel={(option) => t(option.i18n_label)}
                  showSearch={false}
                  pinSelected={false}
                >
                  <Select.Trigger variant="pill-md" appendIcon={null} aria-label={t("email_frequency")}>
                    {selectedOption ? t(selectedOption.i18n_label) : t("email_frequency")}
                  </Select.Trigger>
                </Select>
              );
            }}
          />
        }
      />
      <SettingsControlItem
        title={t("property_changes")}
        description={t("property_changes_description")}
        control={
          <Controller
            control={control}
            name="property_change"
            render={({ field: { value, onChange } }) => (
              <Switch
                size="sm"
                checked={value}
                onCheckedChange={(newValue) => {
                  onChange(newValue);
                  void handleSettingChange("property_change", newValue);
                }}
                aria-label={t("property_changes")}
              />
            )}
          />
        }
      />
      <SettingsControlItem
        title={t("state_change")}
        description={t("state_change_description")}
        control={
          <Controller
            control={control}
            name="state_change"
            render={({ field: { value, onChange } }) => (
              <Switch
                size="sm"
                checked={value}
                onCheckedChange={(newValue) => {
                  onChange(newValue);
                  void handleSettingChange("state_change", newValue);
                }}
                aria-label={t("state_change")}
              />
            )}
          />
        }
      />
      <SettingsControlItem
        title={t("issue_completed")}
        description={t("issue_completed_description")}
        control={
          <Controller
            control={control}
            name="issue_completed"
            render={({ field: { value, onChange } }) => (
              <Switch
                size="sm"
                checked={value}
                onCheckedChange={(newValue) => {
                  onChange(newValue);
                  void handleSettingChange("issue_completed", newValue);
                }}
                aria-label={t("issue_completed")}
              />
            )}
          />
        }
      />
      <SettingsControlItem
        title={t("comments")}
        description={t("comments_description")}
        control={
          <Controller
            control={control}
            name="comment"
            render={({ field: { value, onChange } }) => (
              <Switch
                size="sm"
                checked={value}
                onCheckedChange={(newValue) => {
                  onChange(newValue);
                  void handleSettingChange("comment", newValue);
                }}
                aria-label={t("comments")}
              />
            )}
          />
        }
      />
      <SettingsControlItem
        title={t("mentions")}
        description={t("mentions_description")}
        control={
          <Controller
            control={control}
            name="mention"
            render={({ field: { value, onChange } }) => (
              <Switch
                size="sm"
                checked={value}
                onCheckedChange={(newValue) => {
                  onChange(newValue);
                  void handleSettingChange("mention", newValue);
                }}
                aria-label={t("mentions")}
              />
            )}
          />
        }
      />
      <SettingsControlItem
        title={t("project_access_requests")}
        description={t("project_access_requests_description")}
        control={
          <Controller
            control={control}
            name="project_access_request"
            render={({ field: { value, onChange } }) => (
              <Switch
                size="sm"
                checked={value}
                onCheckedChange={(newValue) => {
                  onChange(newValue);
                  void handleSettingChange("project_access_request", newValue);
                }}
                aria-label={t("project_access_requests")}
              />
            )}
          />
        }
      />
    </div>
  );
});
