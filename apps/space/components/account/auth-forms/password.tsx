/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import { observer } from "mobx-react";
import { CloseCircleOutline, HideOutline, ShowOutline } from "@makeplane/propel/icons";
// plane imports
import { useTranslation } from "@plane/i18n";
import { API_BASE_URL, E_PASSWORD_STRENGTH } from "@plane/constants";
import { Button } from "@makeplane/propel/components/button";
import { Input } from "@makeplane/propel/components/input";
import { useSignUpVerificationCode } from "@plane/hooks";
import { AuthService } from "@plane/services";
import { PasswordStrengthIndicator } from "@plane/blocks/auth";
import { getPasswordStrength } from "@plane/utils";
// helpers
import type { EAuthenticationErrorCodes, TAuthErrorInfo } from "@/helpers/authentication.helper";
import { authErrorHandler } from "@/helpers/authentication.helper";
// types
import { EAuthModes, EAuthSteps } from "@/types/auth";

type Props = {
  email: string;
  isPasswordAutoset: boolean;
  isSMTPConfigured: boolean;
  mode: EAuthModes;
  nextPath: string | undefined;
  handleEmailClear: () => void;
  handleAuthStep: (step: EAuthSteps) => void;
  setErrorInfo: (errorInfo: TAuthErrorInfo | undefined) => void;
};

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
  const { email, nextPath, isSMTPConfigured, handleAuthStep, handleEmailClear, mode, setErrorInfo } = props;
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
  // sign-up: the code sent to the address, asked for once the password is set
  const signUpCode = useSignUpVerificationCode({
    // the code email is written in the language picked on this page
    requestCode: () =>
      authService.requestSignUpVerificationCode({ email: passwordFormData.email, language: currentLocale }),
    onRequestStart: () => setErrorInfo(undefined),
    onRequestError: (error) => {
      const errorhandler = authErrorHandler(
        (error as { error_code?: number } | undefined)?.error_code?.toString() as EAuthenticationErrorCodes,
        t,
        passwordFormData.email
      );
      if (errorhandler?.type) setErrorInfo(errorhandler);
    },
  });

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

  const redirectToOneTimeCodeSignIn = async () => {
    handleAuthStep(EAuthSteps.ONE_TIME_CODE);
  };

  const passwordSupport = passwordFormData.password.length > 0 &&
    mode === EAuthModes.SIGN_UP &&
    getPasswordStrength(passwordFormData.password) != E_PASSWORD_STRENGTH.STRENGTH_VALID && (
      <PasswordStrengthIndicator password={passwordFormData.password} isFocused={isPasswordInputFocused} />
    );

  const isButtonDisabled = useMemo(
    () =>
      !(
        !isSubmitting &&
        !signUpCode.isRequesting &&
        !!passwordFormData.password &&
        (mode === EAuthModes.SIGN_UP
          ? getPasswordStrength(passwordFormData.password) === E_PASSWORD_STRENGTH.STRENGTH_VALID &&
            passwordFormData.password === passwordFormData.confirm_password &&
            !signUpCode.isCodeMissing
          : true)
      ),
    [
      isSubmitting,
      signUpCode.isRequesting,
      signUpCode.isCodeMissing,
      mode,
      passwordFormData.confirm_password,
      passwordFormData.password,
    ]
  );

  const password = passwordFormData.password ?? "";
  const confirmPassword = passwordFormData.confirm_password ?? "";
  const renderPasswordMatchError = !isRetryPasswordInputFocused || confirmPassword.length >= password.length;

  const handleCSRFToken = async () => {
    if (!formRef || !formRef.current) return;
    const token = await csrfPromise;
    if (!token?.csrf_token) return;
    const csrfElement = formRef.current.querySelector("input[name=csrfmiddlewaretoken]");
    csrfElement?.setAttribute("value", token?.csrf_token);
  };

  return (
    <form
      ref={formRef}
      className="mt-5 space-y-4"
      method="POST"
      action={`${API_BASE_URL}/auth/spaces/${mode === EAuthModes.SIGN_IN ? "sign-in" : "sign-up"}/`}
      onSubmit={async (event) => {
        event.preventDefault();
        await handleCSRFToken();
        // A new account first gets the code sent to the address, unless no code is asked for
        if (mode === EAuthModes.SIGN_UP && !(await signUpCode.continueToSubmit())) return;
        if (formRef.current) {
          formRef.current.submit();
        }
        setIsSubmitting(true);
      }}
      onError={() => setIsSubmitting(false)}
    >
      <input type="hidden" name="csrfmiddlewaretoken" />
      <input type="hidden" value={passwordFormData.email} name="email" />
      {/* the new account's profile, and so its emails, start in the language picked on this page */}
      {mode === EAuthModes.SIGN_UP && <input type="hidden" value={currentLocale} name="language" />}
      <input type="hidden" value={nextPath} name="next_path" />
      <div className="space-y-1">
        <label className="text-13 font-medium text-tertiary" htmlFor="email">
          {t("auth.common.email.label")}
        </label>
        <div className="relative flex h-10 items-center rounded-md border border-subtle bg-surface-1 px-3 [&_input]:disable-autofill-style">
          <Input
            id="email"
            name="email"
            type="email"
            size="xl"
            value={passwordFormData.email}
            onChange={(e) => handleFormChange("email", e.target.value)}
            placeholder={t("auth.common.email.placeholder")}
            disabled
          />
          {passwordFormData.email.length > 0 && (
            <button
              type="button"
              aria-label={t("aria_labels.auth_forms.clear_email")}
              className="absolute right-3 hover:cursor-pointer"
              onClick={handleEmailClear}
              tabIndex={-1}
            >
              <CloseCircleOutline className="h-5 w-5 text-placeholder" />
            </button>
          )}
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-13 font-medium text-tertiary" htmlFor="password">
          {mode === EAuthModes.SIGN_IN ? t("auth.common.password.label") : t("auth.common.password.set_password")}
        </label>
        <div className="relative flex h-10 items-center rounded-md border border-subtle bg-surface-1 pr-12 pl-3 [&_input]:disable-autofill-style">
          <Input
            id="password"
            type={showPassword?.password ? "text" : "password"}
            name="password"
            size="xl"
            value={passwordFormData.password}
            onChange={(e) => handleFormChange("password", e.target.value)}
            placeholder={t("auth.common.password.placeholder")}
            onFocus={() => setIsPasswordInputFocused(true)}
            onBlur={() => setIsPasswordInputFocused(false)}
            autoComplete="off"
            // oxlint-disable-next-line jsx-a11y/no-autofocus -- sole primary field of a dedicated auth step; matches standard sign-in flows
            autoFocus
          />
          {showPassword?.password ? (
            <button
              type="button"
              aria-label={t("aria_labels.auth_forms.hide_password")}
              className="absolute right-3 hover:cursor-pointer"
              onClick={() => handleShowPassword("password")}
            >
              <HideOutline className="h-5 w-5 text-placeholder" />
            </button>
          ) : (
            <button
              type="button"
              aria-label={t("aria_labels.auth_forms.show_password")}
              className="absolute right-3 hover:cursor-pointer"
              onClick={() => handleShowPassword("password")}
            >
              <ShowOutline className="h-5 w-5 text-placeholder" />
            </button>
          )}
        </div>
        {passwordSupport}
      </div>

      {mode === EAuthModes.SIGN_UP && (
        <div className="space-y-1">
          <label className="text-13 font-medium text-tertiary" htmlFor="confirm_password">
            {t("auth.common.password.confirm_password.label")}
          </label>
          <div className="relative flex h-10 items-center rounded-md border border-subtle bg-surface-1 pr-12 pl-3 [&_input]:disable-autofill-style">
            <Input
              id="confirm_password"
              type={showPassword?.retypePassword ? "text" : "password"}
              name="confirm_password"
              size="xl"
              value={passwordFormData.confirm_password}
              onChange={(e) => handleFormChange("confirm_password", e.target.value)}
              placeholder={t("auth.common.password.confirm_password.placeholder")}
              onFocus={() => setIsRetryPasswordInputFocused(true)}
              onBlur={() => setIsRetryPasswordInputFocused(false)}
              autoComplete="off"
            />
            {showPassword?.retypePassword ? (
              <button
                type="button"
                aria-label={t("aria_labels.auth_forms.hide_password")}
                className="absolute right-3 hover:cursor-pointer"
                onClick={() => handleShowPassword("retypePassword")}
              >
                <HideOutline className="h-5 w-5 text-placeholder" />
              </button>
            ) : (
              <button
                type="button"
                aria-label={t("aria_labels.auth_forms.show_password")}
                className="absolute right-3 hover:cursor-pointer"
                onClick={() => handleShowPassword("retypePassword")}
              >
                <ShowOutline className="h-5 w-5 text-placeholder" />
              </button>
            )}
          </div>
          {!!passwordFormData.confirm_password &&
            passwordFormData.password !== passwordFormData.confirm_password &&
            renderPasswordMatchError && (
              <span className="text-13 text-danger-primary">{t("auth.common.password.errors.match")}</span>
            )}
        </div>
      )}

      {mode === EAuthModes.SIGN_UP && signUpCode.isCodeStep && (
        <div className="space-y-1">
          <label className="text-13 font-medium text-tertiary" htmlFor="sign-up-code">
            {t("auth.common.one_time_code.label")}
          </label>
          <div className="relative flex h-10 items-center rounded-md border border-subtle bg-surface-1 px-3 [&_input]:disable-autofill-style">
            <Input
              id="sign-up-code"
              name="code"
              size="xl"
              value={signUpCode.code}
              onChange={(e) => signUpCode.setCode(e.target.value)}
              placeholder={t("auth.common.one_time_code.enter_code")}
              inputMode="numeric"
              autoComplete="one-time-code"
              // oxlint-disable-next-line jsx-a11y/no-autofocus -- the code is the only thing left to fill in at this step
              autoFocus
            />
          </div>
          <div className="flex w-full items-center justify-end px-1 pt-1 text-11">
            <button
              type="button"
              onClick={() => void signUpCode.requestCode()}
              className={
                signUpCode.isRequesting || signUpCode.resendTimer > 0
                  ? "text-placeholder"
                  : "font-medium text-accent-secondary hover:text-accent-secondary"
              }
              disabled={signUpCode.isRequesting || signUpCode.resendTimer > 0}
            >
              {signUpCode.resendTimer > 0
                ? t("auth.common.resend_in", { seconds: signUpCode.resendTimer })
                : signUpCode.isRequesting
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
                variant="secondary"
                size="lg"
                stretch="full"
                label={t("auth.common.sign_in_with_one_time_code")}
                onClick={redirectToOneTimeCodeSignIn}
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
            loading={isSubmitting || signUpCode.isRequesting}
            label={
              signUpCode.isRequesting && !signUpCode.isCodeStep
                ? t("auth.common.one_time_code.sending_code")
                : t("app_text.auth_password.create_account")
            }
          />
        )}
      </div>
    </form>
  );
});
