/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { Link } from "react-router";
// local imports
import { renderTaggedText } from "./tagged-text";

export enum EPageTypes {
  INIT = "INIT",
  PUBLIC = "PUBLIC",
  NON_AUTHENTICATED = "NON_AUTHENTICATED",
  ONBOARDING = "ONBOARDING",
  AUTHENTICATED = "AUTHENTICATED",
}

export enum EErrorAlertType {
  BANNER_ALERT = "BANNER_ALERT",
  TOAST_ALERT = "TOAST_ALERT",
  INLINE_FIRST_NAME = "INLINE_FIRST_NAME",
  INLINE_EMAIL = "INLINE_EMAIL",
  INLINE_PASSWORD = "INLINE_PASSWORD",
  INLINE_EMAIL_CODE = "INLINE_EMAIL_CODE",
}

export enum EAuthenticationErrorCodes {
  // Global
  INSTANCE_NOT_CONFIGURED = "5000",
  INVALID_EMAIL = "5005",
  EMAIL_REQUIRED = "5010",
  SIGNUP_DISABLED = "5015",
  // Password strength
  INVALID_PASSWORD = "5020",
  SMTP_NOT_CONFIGURED = "5025",
  // Sign Up
  USER_ALREADY_EXIST = "5030",
  AUTHENTICATION_FAILED_SIGN_UP = "5035",
  REQUIRED_EMAIL_PASSWORD_SIGN_UP = "5040",
  INVALID_EMAIL_SIGN_UP = "5045",
  INVALID_EMAIL_MAGIC_SIGN_UP = "5050",
  MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED = "5055",
  // Sign In
  BOT_USER_LOGIN_FORBIDDEN = "5017",
  USER_ACCOUNT_DEACTIVATED = "5019",
  USER_DOES_NOT_EXIST = "5060",
  AUTHENTICATION_FAILED_SIGN_IN = "5065",
  REQUIRED_EMAIL_PASSWORD_SIGN_IN = "5070",
  INVALID_EMAIL_SIGN_IN = "5075",
  INVALID_EMAIL_MAGIC_SIGN_IN = "5080",
  MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED = "5085",
  // Both Sign in and Sign up for magic
  INVALID_MAGIC_CODE_SIGN_IN = "5090",
  INVALID_MAGIC_CODE_SIGN_UP = "5092",
  EXPIRED_MAGIC_CODE_SIGN_IN = "5095",
  EXPIRED_MAGIC_CODE_SIGN_UP = "5097",
  EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_IN = "5100",
  EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP = "5102",
  // Oauth
  OAUTH_NOT_CONFIGURED = "5104",
  GOOGLE_NOT_CONFIGURED = "5105",
  GITHUB_NOT_CONFIGURED = "5110",
  GITLAB_NOT_CONFIGURED = "5111",
  GOOGLE_OAUTH_PROVIDER_ERROR = "5115",
  GITHUB_OAUTH_PROVIDER_ERROR = "5120",
  GITLAB_OAUTH_PROVIDER_ERROR = "5121",
  // Reset Password
  INVALID_PASSWORD_TOKEN = "5125",
  EXPIRED_PASSWORD_TOKEN = "5130",
  // Change password
  INCORRECT_OLD_PASSWORD = "5135",
  MISSING_PASSWORD = "5138",
  INVALID_NEW_PASSWORD = "5140",
  // set password
  PASSWORD_ALREADY_SET = "5145",
  // Admin
  ADMIN_ALREADY_EXIST = "5150",
  REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME = "5155",
  INVALID_ADMIN_EMAIL = "5160",
  INVALID_ADMIN_PASSWORD = "5165",
  REQUIRED_ADMIN_EMAIL_PASSWORD = "5170",
  ADMIN_AUTHENTICATION_FAILED = "5175",
  ADMIN_USER_ALREADY_EXIST = "5180",
  ADMIN_USER_DOES_NOT_EXIST = "5185",
}

export type TAuthErrorInfo = {
  type: EErrorAlertType;
  code: EAuthenticationErrorCodes;
  title: string;
  message: React.ReactNode;
};

type TTranslate = (key: string, params?: Record<string, unknown>) => string;

type TErrorCopy = {
  /** Translation key of the alert title. */
  title: string;
  message: (t: TTranslate, email?: string) => React.ReactNode;
};

// "{title}. Please try again." and "{title}. Please contact your administrator." share one template
// each, so the title is translated once and the sentence structure once per language.
const tryAgain = (titleKey: string) => (t: TTranslate) => t("auth.error_alerts.try_again", { title: t(titleKey) });
const contactAdmin = (titleKey: string) => (t: TTranslate) =>
  t("auth.error_alerts.contact_admin", { title: t(titleKey) });

/** Renders a `<link>…</link>` tag inside a translated message as a link to `to`. */
const linkMessage = (text: string, to: string): React.ReactNode => (
  <div>
    {renderTaggedText(text, {
      link: (label) => (
        <Link className="font-medium underline underline-offset-4 transition-all hover:font-bold" to={to}>
          {label}
        </Link>
      ),
    })}
  </div>
);

// Keys are spelled out in full (not built from the code name) so they stay greppable.
const errorCodeMessages: { [key in EAuthenticationErrorCodes]: TErrorCopy } = {
  // global
  [EAuthenticationErrorCodes.INSTANCE_NOT_CONFIGURED]: {
    title: "auth.error_alerts.titles.instance_not_configured",
    message: contactAdmin("auth.error_alerts.titles.instance_not_configured"),
  },
  [EAuthenticationErrorCodes.SIGNUP_DISABLED]: {
    title: "auth.error_alerts.titles.sign_up_disabled",
    message: contactAdmin("auth.error_alerts.titles.sign_up_disabled"),
  },
  [EAuthenticationErrorCodes.INVALID_PASSWORD]: {
    title: "auth.error_alerts.titles.invalid_password",
    message: tryAgain("auth.error_alerts.titles.invalid_password"),
  },
  [EAuthenticationErrorCodes.SMTP_NOT_CONFIGURED]: {
    title: "auth.error_alerts.titles.smtp_not_configured",
    message: contactAdmin("auth.error_alerts.titles.smtp_not_configured"),
  },

  // email check in both sign up and sign in
  [EAuthenticationErrorCodes.INVALID_EMAIL]: {
    title: "auth.error_alerts.titles.invalid_email",
    message: tryAgain("auth.error_alerts.titles.invalid_email"),
  },
  [EAuthenticationErrorCodes.EMAIL_REQUIRED]: {
    title: "auth.error_alerts.titles.email_required",
    message: tryAgain("auth.error_alerts.titles.email_required"),
  },

  // sign up
  [EAuthenticationErrorCodes.USER_ALREADY_EXIST]: {
    title: "auth.error_alerts.titles.user_already_exists",
    message: (t, email) =>
      linkMessage(
        t("auth.error_alerts.user_already_exists_message"),
        `/sign-in${email ? `?email=${encodeURIComponent(email)}` : ``}`
      ),
  },
  [EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_UP]: {
    title: "auth.error_alerts.titles.email_and_password_required",
    message: tryAgain("auth.error_alerts.titles.email_and_password_required"),
  },
  [EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_UP]: {
    title: "auth.error_alerts.titles.authentication_failed",
    message: tryAgain("auth.error_alerts.titles.authentication_failed"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_UP]: {
    title: "auth.error_alerts.titles.invalid_email",
    message: tryAgain("auth.error_alerts.titles.invalid_email"),
  },
  [EAuthenticationErrorCodes.MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED]: {
    title: "auth.error_alerts.titles.email_and_code_required",
    message: tryAgain("auth.error_alerts.titles.email_and_code_required"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_UP]: {
    title: "auth.error_alerts.titles.invalid_email",
    message: tryAgain("auth.error_alerts.titles.invalid_email"),
  },

  // sign in
  [EAuthenticationErrorCodes.BOT_USER_LOGIN_FORBIDDEN]: {
    title: "auth.error_alerts.titles.sign_in_not_allowed",
    message: (t) => t("auth.error_alerts.sign_in_not_allowed_message"),
  },
  // Plane's original behaviour was to show "User account deactivated. Please contact {SUPPORT_EMAIL}." using the
  // auth.error_alerts.user_account_deactivated_contact message. That message is kept in the locale files but unused
  // while SUPPORT_EMAIL is disabled (see packages/constants/src/endpoints.ts); this is the fallback it used.
  [EAuthenticationErrorCodes.USER_ACCOUNT_DEACTIVATED]: {
    title: "auth.error_alerts.titles.user_account_deactivated",
    message: (t) =>
      t("auth.error_alerts.contact_admin", { title: t("auth.error_alerts.titles.user_account_deactivated") }),
  },

  [EAuthenticationErrorCodes.USER_DOES_NOT_EXIST]: {
    title: "auth.error_alerts.titles.user_does_not_exist",
    message: (t, email) =>
      linkMessage(
        t("auth.error_alerts.user_does_not_exist_message"),
        `/${email ? `?email=${encodeURIComponent(email)}` : ``}`
      ),
  },
  [EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_IN]: {
    title: "auth.error_alerts.titles.email_and_password_required",
    message: tryAgain("auth.error_alerts.titles.email_and_password_required"),
  },
  [EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_IN]: {
    title: "auth.error_alerts.titles.authentication_failed",
    message: tryAgain("auth.error_alerts.titles.authentication_failed"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_IN]: {
    title: "auth.error_alerts.titles.invalid_email",
    message: tryAgain("auth.error_alerts.titles.invalid_email"),
  },
  [EAuthenticationErrorCodes.MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED]: {
    title: "auth.error_alerts.titles.email_and_code_required",
    message: tryAgain("auth.error_alerts.titles.email_and_code_required"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_IN]: {
    title: "auth.error_alerts.titles.invalid_email",
    message: tryAgain("auth.error_alerts.titles.invalid_email"),
  },

  // Both Sign in and Sign up
  [EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_IN]: {
    title: "auth.error_alerts.titles.authentication_failed",
    message: tryAgain("auth.error_alerts.titles.invalid_magic_code"),
  },
  [EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_UP]: {
    title: "auth.error_alerts.titles.authentication_failed",
    message: tryAgain("auth.error_alerts.titles.invalid_magic_code"),
  },
  [EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_IN]: {
    title: "auth.error_alerts.titles.expired_magic_code",
    message: tryAgain("auth.error_alerts.titles.expired_magic_code"),
  },
  [EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_UP]: {
    title: "auth.error_alerts.titles.expired_magic_code",
    message: tryAgain("auth.error_alerts.titles.expired_magic_code"),
  },
  [EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_IN]: {
    title: "auth.error_alerts.titles.expired_magic_code",
    message: tryAgain("auth.error_alerts.titles.expired_magic_code"),
  },
  [EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP]: {
    title: "auth.error_alerts.titles.expired_magic_code",
    message: tryAgain("auth.error_alerts.titles.expired_magic_code"),
  },

  // Oauth
  [EAuthenticationErrorCodes.OAUTH_NOT_CONFIGURED]: {
    title: "auth.error_alerts.titles.oauth_not_configured",
    message: contactAdmin("auth.error_alerts.titles.oauth_not_configured"),
  },
  [EAuthenticationErrorCodes.GOOGLE_NOT_CONFIGURED]: {
    title: "auth.error_alerts.titles.google_not_configured",
    message: contactAdmin("auth.error_alerts.titles.google_not_configured"),
  },
  [EAuthenticationErrorCodes.GITHUB_NOT_CONFIGURED]: {
    title: "auth.error_alerts.titles.github_not_configured",
    message: contactAdmin("auth.error_alerts.titles.github_not_configured"),
  },
  [EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED]: {
    title: "auth.error_alerts.titles.gitlab_not_configured",
    message: contactAdmin("auth.error_alerts.titles.gitlab_not_configured"),
  },
  [EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR]: {
    title: "auth.error_alerts.titles.google_oauth_provider_error",
    message: tryAgain("auth.error_alerts.titles.google_oauth_provider_error"),
  },
  [EAuthenticationErrorCodes.GITHUB_OAUTH_PROVIDER_ERROR]: {
    title: "auth.error_alerts.titles.github_oauth_provider_error",
    message: tryAgain("auth.error_alerts.titles.github_oauth_provider_error"),
  },
  [EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR]: {
    title: "auth.error_alerts.titles.gitlab_oauth_provider_error",
    message: tryAgain("auth.error_alerts.titles.gitlab_oauth_provider_error"),
  },

  // Reset Password
  [EAuthenticationErrorCodes.INVALID_PASSWORD_TOKEN]: {
    title: "auth.error_alerts.titles.invalid_password_token",
    message: tryAgain("auth.error_alerts.titles.invalid_password_token"),
  },
  [EAuthenticationErrorCodes.EXPIRED_PASSWORD_TOKEN]: {
    title: "auth.error_alerts.titles.expired_password_token",
    message: tryAgain("auth.error_alerts.titles.expired_password_token"),
  },

  // Change password
  [EAuthenticationErrorCodes.MISSING_PASSWORD]: {
    title: "auth.error_alerts.titles.password_required",
    message: tryAgain("auth.error_alerts.titles.password_required"),
  },
  [EAuthenticationErrorCodes.INCORRECT_OLD_PASSWORD]: {
    title: "auth.error_alerts.titles.incorrect_old_password",
    message: tryAgain("auth.error_alerts.titles.incorrect_old_password"),
  },
  [EAuthenticationErrorCodes.INVALID_NEW_PASSWORD]: {
    title: "auth.error_alerts.titles.invalid_new_password",
    message: tryAgain("auth.error_alerts.titles.invalid_new_password"),
  },

  // set password
  [EAuthenticationErrorCodes.PASSWORD_ALREADY_SET]: {
    title: "auth.error_alerts.titles.password_already_set",
    message: tryAgain("auth.error_alerts.titles.password_already_set"),
  },

  // admin
  [EAuthenticationErrorCodes.ADMIN_ALREADY_EXIST]: {
    title: "auth.error_alerts.titles.admin_already_exists",
    message: tryAgain("auth.error_alerts.titles.admin_already_exists"),
  },
  [EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME]: {
    title: "auth.error_alerts.titles.email_password_first_name_required",
    message: tryAgain("auth.error_alerts.titles.email_password_first_name_required"),
  },
  [EAuthenticationErrorCodes.INVALID_ADMIN_EMAIL]: {
    title: "auth.error_alerts.titles.invalid_admin_email",
    message: tryAgain("auth.error_alerts.titles.invalid_admin_email"),
  },
  [EAuthenticationErrorCodes.INVALID_ADMIN_PASSWORD]: {
    title: "auth.error_alerts.titles.invalid_admin_password",
    message: tryAgain("auth.error_alerts.titles.invalid_admin_password"),
  },
  [EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD]: {
    title: "auth.error_alerts.titles.email_and_password_required",
    message: tryAgain("auth.error_alerts.titles.email_and_password_required"),
  },
  [EAuthenticationErrorCodes.ADMIN_AUTHENTICATION_FAILED]: {
    title: "auth.error_alerts.titles.authentication_failed",
    message: tryAgain("auth.error_alerts.titles.authentication_failed"),
  },
  [EAuthenticationErrorCodes.ADMIN_USER_ALREADY_EXIST]: {
    title: "auth.error_alerts.titles.admin_user_already_exists",
    message: (t) => linkMessage(t("auth.error_alerts.admin_user_already_exists_message"), `/admin`),
  },
  [EAuthenticationErrorCodes.ADMIN_USER_DOES_NOT_EXIST]: {
    title: "auth.error_alerts.titles.admin_user_does_not_exist",
    message: (t) => linkMessage(t("auth.error_alerts.admin_user_does_not_exist_message"), `/admin`),
  },
};

export const authErrorHandler = (
  errorCode: EAuthenticationErrorCodes,
  t: TTranslate,
  email?: string
): TAuthErrorInfo | undefined => {
  const bannerAlertErrorCodes = [
    EAuthenticationErrorCodes.INSTANCE_NOT_CONFIGURED,
    EAuthenticationErrorCodes.INVALID_EMAIL,
    EAuthenticationErrorCodes.EMAIL_REQUIRED,
    EAuthenticationErrorCodes.SIGNUP_DISABLED,
    EAuthenticationErrorCodes.INVALID_PASSWORD,
    EAuthenticationErrorCodes.SMTP_NOT_CONFIGURED,
    EAuthenticationErrorCodes.USER_ALREADY_EXIST,
    EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_UP,
    EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_UP,
    EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_UP,
    EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_UP,
    EAuthenticationErrorCodes.MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED,
    EAuthenticationErrorCodes.USER_DOES_NOT_EXIST,
    EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_IN,
    EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_IN,
    EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_IN,
    EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_IN,
    EAuthenticationErrorCodes.MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED,
    EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_IN,
    EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_UP,
    EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_IN,
    EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_UP,
    EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_IN,
    EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP,
    EAuthenticationErrorCodes.OAUTH_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GOOGLE_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GITHUB_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR,
    EAuthenticationErrorCodes.GITHUB_OAUTH_PROVIDER_ERROR,
    EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR,
    EAuthenticationErrorCodes.INVALID_PASSWORD_TOKEN,
    EAuthenticationErrorCodes.EXPIRED_PASSWORD_TOKEN,
    EAuthenticationErrorCodes.INCORRECT_OLD_PASSWORD,
    EAuthenticationErrorCodes.INVALID_NEW_PASSWORD,
    EAuthenticationErrorCodes.PASSWORD_ALREADY_SET,
    EAuthenticationErrorCodes.ADMIN_ALREADY_EXIST,
    EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME,
    EAuthenticationErrorCodes.INVALID_ADMIN_EMAIL,
    EAuthenticationErrorCodes.INVALID_ADMIN_PASSWORD,
    EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD,
    EAuthenticationErrorCodes.ADMIN_AUTHENTICATION_FAILED,
    EAuthenticationErrorCodes.ADMIN_USER_ALREADY_EXIST,
    EAuthenticationErrorCodes.ADMIN_USER_DOES_NOT_EXIST,
    EAuthenticationErrorCodes.BOT_USER_LOGIN_FORBIDDEN,
    EAuthenticationErrorCodes.USER_ACCOUNT_DEACTIVATED,
  ];

  if (bannerAlertErrorCodes.includes(errorCode))
    return {
      type: EErrorAlertType.BANNER_ALERT,
      code: errorCode,
      title: errorCodeMessages[errorCode]?.title ? t(errorCodeMessages[errorCode].title) : t("error"),
      message: errorCodeMessages[errorCode]?.message(t, email) || t("common.errors.default.message"),
    };

  return undefined;
};
