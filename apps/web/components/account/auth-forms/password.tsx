/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
// icons
import { CloseCircleOutline, HideOutline, ShowOutline } from "@makeplane/propel/icons";
// plane imports
import { Banner } from "@makeplane/propel/components/banner";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { API_BASE_URL, E_PASSWORD_STRENGTH } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { PasswordStrengthIndicator } from "@plane/blocks/auth";
import { getPasswordStrength } from "@plane/utils";
// components
import { ForgotPasswordPopover } from "@/components/account/auth-forms/forgot-password-popover";
// constants
// helpers
import type { TAuthErrorInfo } from "@/helpers/authentication.helper";
import { EAuthModes, EAuthSteps, authErrorHandler } from "@/helpers/authentication.helper";
import type { EAuthenticationErrorCodes } from "@/helpers/authentication.helper";
// hooks
import useTimer from "@/hooks/use-timer";
// services
import { AuthService } from "@/services/auth.service";

type Props = {
  email: string;
  isSMTPConfigured: boolean;
  mode: EAuthModes;
  handleEmailClear: () => void;
  handleAuthStep: (step: EAuthSteps) => void;
  nextPath: string | undefined;
  setErrorInfo: (errorInfo: TAuthErrorInfo | undefined) => void;
};

// Seconds before another sign-up code can be asked for
const RESEND_CODE_AFTER_SECONDS = 30;

type TPasswordFormValues = {
  email: string;
  password: string;
  confirm_password?: string;
};

const defaultValues: TPasswordFormValues = {
  email: "",
  password: "",
};

const authService = new AuthService();

export const AuthPasswordForm = observer(function AuthPasswordForm(props: Props) {
  const { email, isSMTPConfigured, handleAuthStep, handleEmailClear, mode, nextPath, setErrorInfo } = props;
  // plane imports
  const { t, currentLocale } = useTranslation();
  // ref
  const formRef = useRef<HTMLFormElement>(null);
  // states
  const [csrfPromise, setCsrfPromise] = useState<Promise<{ csrf_token: string }> | undefined>(undefined);
  const [passwordFormData, setPasswordFormData] = useState<TPasswordFormValues>({ ...defaultValues, email });
  const [showPassword, setShowPassword] = useState({
    password: false,
    retypePassword: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPasswordInputFocused, setIsPasswordInputFocused] = useState(false);
  const [isRetryPasswordInputFocused, setIsRetryPasswordInputFocused] = useState(false);
  const [isBannerMessage, setBannerMessage] = useState(false);
  // sign-up: the code sent to the address, asked for once the password is set
  const [isCodeStep, setIsCodeStep] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const [isRequestingCode, setIsRequestingCode] = useState(false);
  const { timer: resendCodeTimer, setTimer: setResendCodeTimer } = useTimer(0);

  const handleShowPassword = (key: keyof typeof showPassword) =>
    setShowPassword((prev) => ({ ...prev, [key]: !prev[key] }));

  const handleFormChange = (key: keyof TPasswordFormValues, value: string) =>
    setPasswordFormData((prev) => ({ ...prev, [key]: value }));

  useEffect(() => {
    if (csrfPromise === undefined) {
      const promise = authService.requestCSRFToken();
      setCsrfPromise(promise);
    }
  }, [csrfPromise]);

  // Sends the sign-up code; resolves to whether a code is asked for, or undefined when sending failed
  const requestVerificationCode = async (): Promise<boolean | undefined> => {
    setIsRequestingCode(true);
    setErrorInfo(undefined);
    try {
      const response = await authService.requestSignUpVerificationCode({ email: passwordFormData.email });
      if (response?.required) setResendCodeTimer(RESEND_CODE_AFTER_SECONDS);
      return !!response?.required;
    } catch (error) {
      const errorhandler = authErrorHandler(
        (error as { error_code?: number } | undefined)?.error_code?.toString() as EAuthenticationErrorCodes,
        t,
        passwordFormData.email
      );
      if (errorhandler?.type) setErrorInfo(errorhandler);
      return undefined;
    } finally {
      setIsRequestingCode(false);
    }
  };

  const redirectToOneTimeCodeSignIn = async () => {
    handleAuthStep(EAuthSteps.ONE_TIME_CODE);
  };

  const passwordSupport =
    mode === EAuthModes.SIGN_IN ? (
      <div className="w-full">
        {isSMTPConfigured ? (
          <Link
            href={`/accounts/forgot-password?email=${encodeURIComponent(email)}`}
            className="text-11 font-medium text-accent-primary"
          >
            {t("auth.common.forgot_password")}
          </Link>
        ) : (
          <ForgotPasswordPopover />
        )}
      </div>
    ) : (
      passwordFormData.password.length > 0 &&
      getPasswordStrength(passwordFormData.password) != E_PASSWORD_STRENGTH.STRENGTH_VALID && (
        <PasswordStrengthIndicator password={passwordFormData.password} isFocused={isPasswordInputFocused} />
      )
    );

  const isButtonDisabled = useMemo(
    () =>
      !(
        !isSubmitting &&
        !isRequestingCode &&
        !!passwordFormData.password &&
        (mode === EAuthModes.SIGN_UP
          ? passwordFormData.password === passwordFormData.confirm_password &&
            (!isCodeStep || verificationCode.trim().length > 0)
          : true)
      ),
    [
      isSubmitting,
      isRequestingCode,
      isCodeStep,
      verificationCode,
      mode,
      passwordFormData.confirm_password,
      passwordFormData.password,
    ]
  );

  const password = passwordFormData?.password ?? "";
  const confirmPassword = passwordFormData?.confirm_password ?? "";
  const renderPasswordMatchError = !isRetryPasswordInputFocused || confirmPassword.length >= password.length;

  const handleCSRFToken = async () => {
    if (!formRef || !formRef.current) return;
    const token = await csrfPromise;
    if (!token?.csrf_token) return;
    const csrfElement = formRef.current.querySelector("input[name=csrfmiddlewaretoken]");
    csrfElement?.setAttribute("value", token?.csrf_token);
  };

  return (
    <>
      {isBannerMessage && mode === EAuthModes.SIGN_UP && (
        <Banner
          placement="inline"
          variant="danger"
          description={t("auth.sign_up.errors.password.strength")}
          dismissLabel={t("close")}
          onDismiss={() => setBannerMessage(false)}
        />
      )}
      <form
        ref={formRef}
        className="space-y-4"
        method="POST"
        action={`${API_BASE_URL}/auth/${mode === EAuthModes.SIGN_IN ? "sign-in" : "sign-up"}/`}
        onSubmit={async (event) => {
          event.preventDefault(); // Prevent form from submitting by default
          await handleCSRFToken();
          const isPasswordValid =
            mode === EAuthModes.SIGN_UP
              ? getPasswordStrength(passwordFormData.password) === E_PASSWORD_STRENGTH.STRENGTH_VALID
              : true;
          if (!isPasswordValid) {
            setBannerMessage(true);
            return;
          }
          // A new account first gets the code sent to the address, unless no code is asked for
          if (mode === EAuthModes.SIGN_UP && !isCodeStep) {
            const isCodeRequired = await requestVerificationCode();
            if (isCodeRequired === undefined) return;
            if (isCodeRequired) {
              setIsCodeStep(true);
              return;
            }
          }
          setIsSubmitting(true);
          if (formRef.current) formRef.current.submit(); // Manually submit the form if the condition is met
        }}
        onError={() => {
          setIsSubmitting(false);
        }}
      >
        <input type="hidden" name="csrfmiddlewaretoken" />
        <input type="hidden" value={passwordFormData.email} name="email" />
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
              value={passwordFormData.email}
              onChange={(e) => handleFormChange("email", e.target.value)}
              placeholder={t("auth.common.email.placeholder")}
              disabled
            />
            {passwordFormData.email.length > 0 && (
              <button
                type="button"
                className="grid size-5 place-items-center"
                onClick={handleEmailClear}
                aria-label={t("aria_labels.auth_forms.clear_email")}
              >
                <CloseCircleOutline className="size-5 text-placeholder" />
              </button>
            )}
          </InputGroup>
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-13 font-medium text-tertiary">
            {mode === EAuthModes.SIGN_IN ? t("auth.common.password.label") : t("auth.common.password.set_password")}
          </label>
          <InputGroup size="2xl">
            <Input
              size="2xl"
              type={showPassword?.password ? "text" : "password"}
              id="password"
              name="password"
              value={passwordFormData.password}
              onChange={(e) => handleFormChange("password", e.target.value)}
              placeholder={t("auth.common.password.placeholder")}
              onFocus={() => setIsPasswordInputFocused(true)}
              onBlur={() => setIsPasswordInputFocused(false)}
              autoComplete="off"
              // oxlint-disable-next-line jsx-a11y/no-autofocus -- intentional autofocus; behaviour preserved
              autoFocus
            />
            <button
              type="button"
              onClick={() => handleShowPassword("password")}
              className="grid size-5 place-items-center"
              aria-label={t(
                showPassword?.password ? "aria_labels.auth_forms.hide_password" : "aria_labels.auth_forms.show_password"
              )}
            >
              {showPassword?.password ? (
                <HideOutline className="size-5 text-placeholder" />
              ) : (
                <ShowOutline className="size-5 text-placeholder" />
              )}
            </button>
          </InputGroup>
          {passwordSupport}
        </div>

        {mode === EAuthModes.SIGN_UP && (
          <div className="space-y-1">
            <label htmlFor="confirm-password" className="text-13 font-medium text-tertiary">
              {t("auth.common.password.confirm_password.label")}
            </label>
            <InputGroup size="2xl">
              <Input
                size="2xl"
                type={showPassword?.retypePassword ? "text" : "password"}
                id="confirm-password"
                name="confirm_password"
                value={passwordFormData.confirm_password}
                onChange={(e) => handleFormChange("confirm_password", e.target.value)}
                placeholder={t("auth.common.password.confirm_password.placeholder")}
                onFocus={() => setIsRetryPasswordInputFocused(true)}
                onBlur={() => setIsRetryPasswordInputFocused(false)}
                autoComplete="off"
              />
              <button
                type="button"
                className="grid size-5 place-items-center"
                aria-label={t(
                  showPassword?.retypePassword
                    ? "aria_labels.auth_forms.hide_password"
                    : "aria_labels.auth_forms.show_password"
                )}
                onClick={() => handleShowPassword("retypePassword")}
              >
                {showPassword?.retypePassword ? (
                  <HideOutline className="size-5 text-placeholder" />
                ) : (
                  <ShowOutline className="size-5 text-placeholder" />
                )}
              </button>
            </InputGroup>
            {!!passwordFormData.confirm_password &&
              passwordFormData.password !== passwordFormData.confirm_password &&
              renderPasswordMatchError && (
                <span className="text-13 text-danger-primary">{t("auth.common.password.errors.match")}</span>
              )}
          </div>
        )}

        {mode === EAuthModes.SIGN_UP && isCodeStep && (
          <div className="space-y-1">
            <label htmlFor="sign-up-code" className="text-13 font-medium text-tertiary">
              {t("auth.common.one_time_code.label")}
            </label>
            <InputGroup size="2xl">
              <Input
                size="2xl"
                id="sign-up-code"
                name="code"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                placeholder={t("auth.common.one_time_code.placeholder")}
                inputMode="numeric"
                autoComplete="one-time-code"
                // oxlint-disable-next-line jsx-a11y/no-autofocus -- the code is the only thing left to fill in at this step
                autoFocus
              />
            </InputGroup>
            <div className="flex w-full items-center justify-between px-1 pt-1 text-11">
              {/* A neutral hint: the code is only checked once the form is sent */}
              <p className="font-medium text-tertiary">{t("auth.common.one_time_code.paste_code")}</p>
              <button
                type="button"
                onClick={() => void requestVerificationCode()}
                className={
                  isRequestingCode || resendCodeTimer > 0
                    ? "text-placeholder"
                    : "font-medium text-accent-secondary hover:text-accent-secondary"
                }
                disabled={isRequestingCode || resendCodeTimer > 0}
              >
                {resendCodeTimer > 0
                  ? t("auth.common.resend_in", { seconds: resendCodeTimer })
                  : isRequestingCode
                    ? t("auth.common.one_time_code.requesting_new_code")
                    : t("common.resend")}
              </button>
            </div>
          </div>
        )}

        <div className="space-y-2.5">
          {mode === EAuthModes.SIGN_IN ? (
            <>
              <Button
                type="submit"
                variant="primary"
                size="lg"
                stretch="full"
                disabled={isButtonDisabled}
                loading={isSubmitting}
                label={isSMTPConfigured ? t("common.continue") : t("common.go_to_workspace")}
              />
              {isSMTPConfigured && (
                <Button
                  type="button"
                  onClick={redirectToOneTimeCodeSignIn}
                  variant="secondary"
                  size="lg"
                  stretch="full"
                  label={t("auth.common.sign_in_with_one_time_code")}
                />
              )}
            </>
          ) : (
            <Button
              type="submit"
              variant="primary"
              size="lg"
              stretch="full"
              disabled={isButtonDisabled}
              loading={isSubmitting || isRequestingCode}
              label={
                isRequestingCode && !isCodeStep
                  ? t("auth.common.one_time_code.sending_code")
                  : t("app_text.auth_password.create_account")
              }
            />
          )}
        </div>
      </form>
    </>
  );
});
