/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { KeyOutline, MailOutline } from "@makeplane/propel/icons";
// types
import { OIDC_PROVIDER_DEFINITIONS } from "@plane/constants";
import type {
  TCoreInstanceAuthenticationModeKeys,
  TGetBaseAuthenticationModeProps,
  TInstanceAuthenticationMethodKeys,
  TInstanceAuthenticationModes,
  TOidcProviderKey,
} from "@plane/types";
// assets
import giteaLogo from "@/app/assets/logos/gitea-logo.svg?url";
import githubLightModeImage from "@/app/assets/logos/github-black.png?url";
import githubDarkModeImage from "@/app/assets/logos/github-white.png?url";
import gitlabLogo from "@/app/assets/logos/gitlab-logo.svg?url";
// components
import { EmailCodesConfiguration } from "@/components/authentication/email-config-switch";
import { GiteaConfiguration } from "@/components/authentication/gitea-config";
import { GithubConfiguration } from "@/components/authentication/github-config";
import { GitlabConfiguration } from "@/components/authentication/gitlab-config";
import { OidcConfiguration } from "@/components/authentication/oidc-config";
import { OidcProviderIcon } from "@/components/authentication/oidc-icon";
import { PasswordLoginConfiguration } from "@/components/authentication/password-config-switch";

// Single sign-on providers: described in @plane/constants (OIDC_PROVIDER_DEFINITIONS), the server has the same list
const getOidcMode = (
  key: TOidcProviderKey,
  disabled: boolean,
  updateConfig: TGetBaseAuthenticationModeProps["updateConfig"]
): TInstanceAuthenticationModes => {
  const provider = OIDC_PROVIDER_DEFINITIONS[key];
  return {
    key,
    name: provider.name,
    description: provider.description,
    icon: <OidcProviderIcon icon={provider.icon} name={provider.name} size={20} />,
    config: <OidcConfiguration provider={provider} disabled={disabled} updateConfig={updateConfig} />,
    enabledConfigKey: `IS_${provider.prefix}_ENABLED` as TInstanceAuthenticationMethodKeys,
  };
};

// Authentication methods
export const getCoreAuthenticationModesMap: (
  props: TGetBaseAuthenticationModeProps
) => Record<TCoreInstanceAuthenticationModeKeys, TInstanceAuthenticationModes> = ({
  disabled,
  updateConfig,
  resolvedTheme,
}) => ({
  "unique-codes": {
    key: "unique-codes",
    name: "Unique codes",
    description:
      "Log in or sign up for Pi-Plane using codes sent via email. You need to have set up SMTP to use this method.",
    icon: <MailOutline className="h-6 w-6 p-0.5 text-tertiary" />,
    config: <EmailCodesConfiguration disabled={disabled} updateConfig={updateConfig} />,
    enabledConfigKey: "ENABLE_MAGIC_LINK_LOGIN",
  },
  "passwords-login": {
    key: "passwords-login",
    name: "Passwords",
    description: "Allow members to create accounts with passwords and use it with their email addresses to sign in.",
    icon: <KeyOutline className="h-6 w-6 p-0.5 text-tertiary" />,
    config: <PasswordLoginConfiguration disabled={disabled} updateConfig={updateConfig} />,
    enabledConfigKey: "ENABLE_EMAIL_PASSWORD",
  },
  github: {
    key: "github",
    name: "GitHub",
    description: "Allow members to log in or sign up for Pi-Plane with their GitHub accounts.",
    icon: (
      <img
        src={resolvedTheme === "dark" ? githubDarkModeImage : githubLightModeImage}
        height={20}
        width={20}
        alt="GitHub Logo"
      />
    ),
    config: <GithubConfiguration disabled={disabled} updateConfig={updateConfig} />,
    enabledConfigKey: "IS_GITHUB_ENABLED",
  },
  gitlab: {
    key: "gitlab",
    name: "GitLab",
    description: "Allow members to log in or sign up to plane with their GitLab accounts.",
    icon: <img src={gitlabLogo} height={20} width={20} alt="GitLab Logo" />,
    config: <GitlabConfiguration disabled={disabled} updateConfig={updateConfig} />,
    enabledConfigKey: "IS_GITLAB_ENABLED",
  },
  gitea: {
    key: "gitea",
    name: "Gitea",
    description: "Allow members to log in or sign up to plane with their Gitea accounts.",
    icon: <img src={giteaLogo} height={20} width={20} alt="Gitea Logo" />,
    config: <GiteaConfiguration disabled={disabled} updateConfig={updateConfig} />,
    enabledConfigKey: "IS_GITEA_ENABLED",
  },
  entra: getOidcMode("entra", disabled, updateConfig),
  "google-oidc": getOidcMode("google-oidc", disabled, updateConfig),
  oidc: getOidcMode("oidc", disabled, updateConfig),
});
