/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { useLatestCallback } from "./use-latest-callback";

// Seconds before another sign-up code can be asked for
const DEFAULT_RESEND_AFTER_SECONDS = 30;

export type TUseSignUpVerificationCodeOptions = {
  /** Asks the server to send a code; resolves to whether the instance asks for one at all. */
  requestCode: () => Promise<{ required: boolean } | undefined>;
  /** Called before a request goes out, e.g. to clear an error that is still shown. */
  onRequestStart?: () => void;
  /** Called with whatever the request threw, e.g. to show it. */
  onRequestError?: (error: unknown) => void;
  resendAfterSeconds?: number;
};

/**
 * The code step of the email-and-password sign-up, shared by the web app and Space: once the password is set, a
 * code is sent to the address and asked for in the same form, unless the instance asks for none.
 *
 * ``continueToSubmit`` is called when the form is submitted. It resolves to ``true`` when the form should now go
 * to the server (the code is typed, or none is asked for) and to ``false`` when this submit only moved the form to
 * the code step, or the code could not be sent.
 */
export const useSignUpVerificationCode = (options: TUseSignUpVerificationCodeOptions) => {
  const { resendAfterSeconds = DEFAULT_RESEND_AFTER_SECONDS } = options;
  const [isCodeStep, setIsCodeStep] = useState(false);
  const [code, setCode] = useState("");
  const [isRequesting, setIsRequesting] = useState(false);
  const [resendTimer, setResendTimer] = useState(0);

  const requestCodeLatest = useLatestCallback(options.requestCode);
  const onRequestStartLatest = useLatestCallback(() => options.onRequestStart?.());
  const onRequestErrorLatest = useLatestCallback((error: unknown) => options.onRequestError?.(error));

  // Counts down while there is time left, and stops at zero
  useEffect(() => {
    if (resendTimer <= 0) return;
    const timeout = setTimeout(() => setResendTimer((previous) => previous - 1), 1000);
    return () => clearTimeout(timeout);
  }, [resendTimer]);

  /** Sends a code; resolves to whether one is asked for, or ``undefined`` when sending failed. */
  const requestCode = useCallback(async (): Promise<boolean | undefined> => {
    setIsRequesting(true);
    onRequestStartLatest();
    try {
      const response = await requestCodeLatest();
      const isRequired = !!response?.required;
      if (isRequired) setResendTimer(resendAfterSeconds);
      return isRequired;
    } catch (error) {
      onRequestErrorLatest(error);
      return undefined;
    } finally {
      setIsRequesting(false);
    }
  }, [onRequestErrorLatest, onRequestStartLatest, requestCodeLatest, resendAfterSeconds]);

  const continueToSubmit = useCallback(async (): Promise<boolean> => {
    if (isCodeStep) return true;
    const isRequired = await requestCode();
    if (isRequired === undefined) return false;
    if (isRequired) {
      setIsCodeStep(true);
      return false;
    }
    return true;
  }, [isCodeStep, requestCode]);

  return {
    isCodeStep,
    code,
    setCode,
    /** The code step is shown but nothing is typed yet. */
    isCodeMissing: isCodeStep && code.trim().length === 0,
    isRequesting,
    resendTimer,
    requestCode,
    continueToSubmit,
  };
};
