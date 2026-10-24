/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export type TCoreInstanceAuthenticationModeKeys =
  | "unique-codes"
  | "passwords-login"
  | "github"
  | "gitlab"
  | "gitea"
  | TOidcProviderKey;

/** Single sign-on providers of the server (apps/api/plane/authentication/provider/oidc/registry.py). */
export type TOidcProviderKey = "entra" | "google-oidc" | "oidc";

export type TInstanceAuthenticationModeKeys = TCoreInstanceAuthenticationModeKeys;

export type TInstanceAuthenticationModes = {
  key: TInstanceAuthenticationModeKeys;
  name: string;
  description: string;
  icon: React.ReactNode;
  config: React.ReactNode;
  enabledConfigKey: TInstanceAuthenticationMethodKeys;
  unavailable?: boolean;
};

export type TInstanceAuthenticationMethodKeys =
  | "ENABLE_SIGNUP"
  | "ENABLE_MAGIC_LINK_LOGIN"
  | "ENABLE_EMAIL_PASSWORD"
  | "IS_GITHUB_ENABLED"
  | "IS_GITLAB_ENABLED"
  | "IS_GITEA_ENABLED"
  | "IS_ENTRA_ENABLED"
  | "IS_GOOGLE_OIDC_ENABLED"
  | "IS_OIDC_ENABLED";

export type TInstanceGithubAuthenticationConfigurationKeys =
  | "GITHUB_CLIENT_ID"
  | "GITHUB_CLIENT_SECRET"
  | "GITHUB_ORGANIZATION_ID"
  | "ENABLE_GITHUB_SYNC";

export type TInstanceGitlabAuthenticationConfigurationKeys =
  | "GITLAB_HOST"
  | "GITLAB_CLIENT_ID"
  | "GITLAB_CLIENT_SECRET"
  | "ENABLE_GITLAB_SYNC";

export type TInstanceGiteaAuthenticationConfigurationKeys =
  | "GITEA_HOST"
  | "GITEA_CLIENT_ID"
  | "GITEA_CLIENT_SECRET"
  | "ENABLE_GITEA_SYNC";

export type TInstanceOidcAuthenticationConfigurationKeys =
  | `${"ENTRA" | "GOOGLE_OIDC" | "OIDC"}_${"CLIENT_ID" | "CLIENT_SECRET" | "ENABLE_SIGNUP" | "ALLOWED_EMAIL_DOMAINS" | "LINK_EXISTING_ACCOUNTS"}`
  | `ENABLE_${"ENTRA" | "GOOGLE_OIDC" | "OIDC"}_SYNC`
  | "ENTRA_TENANT_ID"
  | "GOOGLE_OIDC_HOSTED_DOMAIN"
  | "OIDC_ISSUER_URL"
  | "OIDC_DISPLAY_NAME";

export type TInstanceAuthenticationConfigurationKeys =
  | TInstanceGithubAuthenticationConfigurationKeys
  | TInstanceGitlabAuthenticationConfigurationKeys
  | TInstanceGiteaAuthenticationConfigurationKeys
  | TInstanceOidcAuthenticationConfigurationKeys;

export type TInstanceAuthenticationKeys = TInstanceAuthenticationMethodKeys | TInstanceAuthenticationConfigurationKeys;

export type TGetBaseAuthenticationModeProps = {
  disabled: boolean;
  updateConfig: (key: TInstanceAuthenticationMethodKeys, value: string) => void;
  resolvedTheme: string | undefined;
};

export type TOAuthOption = {
  id: string;
  text: string;
  icon: React.ReactNode;
  onClick: () => void;
  enabled?: boolean;
};

export type TOAuthConfigs = {
  isOAuthEnabled: boolean;
  oAuthOptions: TOAuthOption[];
};

export type TCoreLoginMediums = "email" | "magic-code" | "github" | "gitlab" | "google" | "gitea" | TOidcProviderKey;

/** A single sign-on provider that is switched on and configured, as the sign-in screens list it. */
export type TOidcProviderOption = {
  key: TOidcProviderKey;
  name: string;
  icon: "microsoft" | "google" | "key";
};
