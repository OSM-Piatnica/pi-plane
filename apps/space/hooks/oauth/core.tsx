/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import { useSearchParams } from "next/navigation";
import { useTheme } from "next-themes";
import { API_BASE_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TOAuthConfigs, TOAuthOption } from "@plane/types";
// assets
import giteaLogo from "@/app/assets/logos/gitea-logo.svg?url";
import githubLightLogo from "@/app/assets/logos/github-black.png?url";
import githubDarkLogo from "@/app/assets/logos/github-dark.svg?url";
import gitlabLogo from "@/app/assets/logos/gitlab-logo.svg?url";
import googleLogo from "@/app/assets/logos/google-logo.svg?url";
// hooks
import { useInstance } from "@/hooks/store/use-instance";

export type TOAuthAction = "sign_up" | "sign_in" | "continue";

export const useCoreOAuthConfig = (oauthAction: TOAuthAction): TOAuthConfigs => {
  //router
  const searchParams = useSearchParams();
  // query params
  const next_path = searchParams.get("next_path");
  // translation
  const { t } = useTranslation();
  // theme
  const { resolvedTheme } = useTheme();
  // store hooks
  const { config } = useInstance();
  // derived values
  const isOAuthEnabled =
    (config &&
      (config?.is_google_enabled ||
        config?.is_github_enabled ||
        config?.is_gitlab_enabled ||
        config?.is_gitea_enabled)) ||
    false;
  const getActionText = (provider: string): string => {
    if (oauthAction === "sign_up") return t("space_text.oauth.sign_up_with", { provider });
    if (oauthAction === "sign_in") return t("space_text.oauth.sign_in_with", { provider });
    return t("space_text.oauth.continue_with", { provider });
  };
  const oAuthOptions: TOAuthOption[] = [
    {
      id: "google",
      text: getActionText("Google"),
      icon: (
        <img src={googleLogo} height={18} width={18} alt={t("app_text.integrations.logo_alt", { title: "Google" })} />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/google/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_google_enabled,
    },
    {
      id: "github",
      text: getActionText("GitHub"),
      icon: (
        <img
          src={resolvedTheme === "dark" ? githubLightLogo : githubDarkLogo}
          height={18}
          width={18}
          alt={t("app_text.integrations.logo_alt", { title: "GitHub" })}
        />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/github/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_github_enabled,
    },
    {
      id: "gitlab",
      text: getActionText("GitLab"),
      icon: (
        <img src={gitlabLogo} height={18} width={18} alt={t("app_text.integrations.logo_alt", { title: "GitLab" })} />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/gitlab/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_gitlab_enabled,
    },
    {
      id: "gitea",
      text: getActionText("Gitea"),
      icon: (
        <img src={giteaLogo} height={18} width={18} alt={t("app_text.integrations.logo_alt", { title: "Gitea" })} />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/gitea/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_gitea_enabled,
    },
  ];

  return {
    isOAuthEnabled,
    oAuthOptions,
  };
};
