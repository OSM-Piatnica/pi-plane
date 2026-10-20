/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
import { PenTool } from "lucide-react";
import {
  CubeOutline,
  MonitorOutline,
  RefreshOutline,
  RocketOutline,
  TickOutline,
  ViewsOutline,
} from "@makeplane/propel/icons";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import type { TUserProfile } from "@plane/types";
import { EOnboardingSteps } from "@plane/types";
// hooks
import { useUserProfile } from "@/hooks/store/user";
// local components
import { CommonOnboardingHeader } from "../common";
import type { TProfileSetupFormValues } from "../profile/root";

type Props = {
  handleStepChange: (step: EOnboardingSteps, skipInvites?: boolean) => void;
};

const ROLES = [
  { id: "product-manager", labelKey: "onboarding.role.options.product_manager", icon: CubeOutline },
  { id: "engineering-manager", labelKey: "onboarding.role.options.engineering_manager", icon: ViewsOutline },
  { id: "designer", labelKey: "onboarding.role.options.designer", icon: PenTool },
  { id: "developer", labelKey: "onboarding.role.options.developer", icon: MonitorOutline },
  { id: "founder-executive", labelKey: "onboarding.role.options.founder_executive", icon: RocketOutline },
  { id: "operations-manager", labelKey: "onboarding.role.options.operations_manager", icon: RefreshOutline },
  { id: "others", labelKey: "onboarding.role.options.others", icon: CubeOutline },
];

const defaultValues = {
  role: "",
};

export const RoleSetupStep = observer(function RoleSetupStep({ handleStepChange }: Props) {
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { data: profile, updateUserProfile } = useUserProfile();
  // form info
  const {
    handleSubmit,
    control,
    formState: { errors, isSubmitting, isValid },
  } = useForm<TProfileSetupFormValues>({
    defaultValues: {
      ...defaultValues,
      role: profile?.role,
    },
    mode: "onChange",
  });

  // handle submit
  const handleSubmitUserPersonalization = async (formData: TProfileSetupFormValues) => {
    const profileUpdatePayload: Partial<TUserProfile> = {
      role: formData.role,
    };
    try {
      await updateUserProfile(profileUpdatePayload);
      // totalSteps > 2 && stepChange({ profile_complete: true }),
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("onboarding.profile.toast.profile_setup_completed"),
      });
    } catch {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("onboarding.profile.toast.profile_setup_failed"),
      });
    }
  };

  const onSubmit = async (formData: TProfileSetupFormValues) => {
    if (!profile) return;
    await handleSubmitUserPersonalization(formData);
    handleStepChange(EOnboardingSteps.ROLE_SETUP);
  };

  const handleSkip = () => {
    handleStepChange(EOnboardingSteps.ROLE_SETUP);
  };

  const isButtonDisabled = !(!isSubmitting && isValid);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-10">
      {/* Header */}
      <CommonOnboardingHeader title={t("onboarding.role.title")} description={t("onboarding.role.description")} />
      {/* Role Selection */}
      <div className="flex flex-col gap-3">
        <p className="text-body-sm-semibold text-placeholder">{t("onboarding.role.select_one")}</p>
        <Controller
          control={control}
          name="role"
          rules={{
            required: t("common.errors.required"),
          }}
          render={({ field: { value, onChange } }) => (
            <div className="flex flex-col gap-3">
              {ROLES.map((role) => {
                const Icon = role.icon;
                const isSelected = value === role.id;

                return (
                  <button
                    type="button"
                    key={role.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      onChange(role.id);
                    }}
                    className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 transition-all duration-200 ${
                      isSelected
                        ? "border-accent-strong bg-accent-subtle text-accent-primary"
                        : "border-subtle text-tertiary hover:border-strong"
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className="size-3.5" />
                      <span className="text-body-sm-semibold">{t(role.labelKey)}</span>
                    </div>
                    {isSelected && (
                      <>
                        <span
                          className={`border-blue-500 flex size-4 items-center justify-center rounded-sm border-2 bg-accent-primary`}
                        >
                          <TickOutline className="h-3 w-3 text-on-color" />
                        </span>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        />
        {errors.role && <span className="text-13 text-danger-primary">{errors.role.message}</span>}
      </div>
      {/* Action Buttons */}
      <div className="space-y-3">
        <Button
          variant="primary"
          type="submit"
          stretch="full"
          size="lg"
          disabled={isButtonDisabled}
          label={t("common.continue")}
        />
        <Button
          variant="ghost"
          onClick={handleSkip}
          stretch="full"
          size="lg"
          render={<button type="button" className="text-tertiary" />}
          label={t("onboarding.skip")}
        />
      </div>
    </form>
  );
});
