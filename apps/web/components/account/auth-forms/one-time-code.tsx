/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { CloseCircleOutline, TickCircleOutline } from "@makeplane/propel/icons";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { API_BASE_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
// constants
// helpers
import { EAuthModes } from "@/helpers/authentication.helper";
// hooks
import useTimer from "@/hooks/use-timer";
// services
import { AuthService } from "@/services/auth.service";

// services
const authService = new AuthService();

type TAuthOneTimeCodeForm = {
  mode: EAuthModes;
  email: string;
  isExistingEmail: boolean;
  handleEmailClear: () => void;
  generateEmailOneTimeCode: (email: string) => Promise<{ code: string } | undefined>;
  nextPath: string | undefined;
};

type TOneTimeCodeFormValues = {
  email: string;
  code: string;
};

const defaultValues: TOneTimeCodeFormValues = {
  email: "",
  code: "",
};

export function AuthOneTimeCodeForm(props: TAuthOneTimeCodeForm) {
  const { mode, email, handleEmailClear, generateEmailOneTimeCode, nextPath } = props;
  // derived values
  const defaultResetTimerValue = 5;
  // states
  const [oneTimeCodeFormData, setOneTimeCodeFormData] = useState<TOneTimeCodeFormValues>({ ...defaultValues, email });
  const [isRequestingNewCode, setIsRequestingNewCode] = useState(false);
  const [csrfToken, setCsrfToken] = useState<string | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // timer
  const { timer: resendTimerCode, setTimer: setResendCodeTimer } = useTimer(0);
  // plane hooks
  const { t, currentLocale } = useTranslation();

  const handleFormChange = (key: keyof TOneTimeCodeFormValues, value: string) =>
    setOneTimeCodeFormData((prev) => ({ ...prev, [key]: value }));

  const generateNewCode = async (emailAddress: string) => {
    try {
      setIsRequestingNewCode(true);
      const oneTimeCode = await generateEmailOneTimeCode(emailAddress);
      setResendCodeTimer(defaultResetTimerValue);
      handleFormChange("code", oneTimeCode?.code || "");
      setIsRequestingNewCode(false);
    } catch {
      setResendCodeTimer(0);
      console.error("Error while requesting new code");
      setIsRequestingNewCode(false);
    }
  };

  useEffect(() => {
    if (csrfToken === undefined)
      authService.requestCSRFToken().then((data) => data?.csrf_token && setCsrfToken(data.csrf_token));
  }, [csrfToken]);

  const isRequestNewCodeDisabled = isRequestingNewCode || resendTimerCode > 0;
  const isButtonDisabled = isRequestingNewCode || !oneTimeCodeFormData.code || isSubmitting;

  return (
    <form
      className="space-y-4"
      method="POST"
      action={`${API_BASE_URL}/auth/${mode === EAuthModes.SIGN_IN ? "magic-sign-in" : "magic-sign-up"}/`}
      onSubmit={() => {
        setIsSubmitting(true);
      }}
      onError={() => {
        setIsSubmitting(false);
      }}
    >
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken ?? ""} />
      <input type="hidden" value={oneTimeCodeFormData.email} name="email" />
      {mode === EAuthModes.SIGN_UP && <input type="hidden" value={currentLocale} name="language" />}
      {nextPath && <input type="hidden" value={nextPath} name="next_path" />}
      <div className="space-y-1">
        <label htmlFor="email" className="text-13 font-medium text-tertiary">
          {t("auth.common.email.label")}
        </label>
        <InputGroup size="2xl">
          <Input
            size="2xl"
            id="email"
            name="email"
            type="email"
            value={oneTimeCodeFormData.email}
            onChange={(e) => handleFormChange("email", e.target.value)}
            placeholder={t("auth.common.email.placeholder")}
            autoComplete="off"
            disabled
          />
          {oneTimeCodeFormData.email.length > 0 && (
            <button
              type="button"
              className="grid size-5 place-items-center"
              aria-label={t("aria_labels.auth_forms.clear_email")}
              onClick={handleEmailClear}
            >
              <CloseCircleOutline className="size-5 text-placeholder" />
            </button>
          )}
        </InputGroup>
      </div>

      <div className="space-y-1">
        <label htmlFor="one-time-code" className="text-13 font-medium text-tertiary">
          {t("auth.common.one_time_code.label")}
        </label>
        <InputGroup size="2xl">
          <Input
            size="2xl"
            name="code"
            id="one-time-code"
            value={oneTimeCodeFormData.code}
            onChange={(e) => handleFormChange("code", e.target.value)}
            placeholder={t("auth.common.one_time_code.placeholder")}
            autoComplete="off"
            // oxlint-disable-next-line jsx-a11y/no-autofocus -- existing behaviour; a11y handled separately
            autoFocus
          />
        </InputGroup>
        <div className="flex w-full items-center justify-between px-1 pt-1 text-11">
          <p className="flex items-center gap-1 font-medium text-success-primary">
            <TickCircleOutline height={12} width={12} />
            {t("auth.common.one_time_code.paste_code")}
          </p>
          <button
            type="button"
            onClick={() => generateNewCode(oneTimeCodeFormData.email)}
            className={
              isRequestNewCodeDisabled
                ? "text-placeholder"
                : "font-medium text-accent-secondary hover:text-accent-secondary"
            }
            disabled={isRequestNewCodeDisabled}
          >
            {resendTimerCode > 0
              ? t("auth.common.resend_in", { seconds: resendTimerCode })
              : isRequestingNewCode
                ? t("auth.common.one_time_code.requesting_new_code")
                : t("common.resend")}
          </button>
        </div>
      </div>

      <div className="space-y-2.5">
        <Button
          type="submit"
          variant="primary"
          size="lg"
          stretch="full"
          disabled={isButtonDisabled}
          loading={isSubmitting}
          label={isRequestingNewCode ? t("auth.common.one_time_code.sending_code") : t("common.continue")}
        />
      </div>
    </form>
  );
}
