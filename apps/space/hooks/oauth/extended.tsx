/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import { KeyOutline } from "@makeplane/propel/icons";
import { useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TOAuthConfigs, TOidcProviderOption } from "@plane/types";
// assets
import googleLogo from "@/app/assets/logos/google-logo.svg?url";
import microsoftLogo from "@/app/assets/logos/microsoft-logo.svg?url";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
// local imports
import type { TOAuthAction } from "./core";

/** The single sign-on providers (OpenID Connect) that the server lists as configured. */
export const useExtendedOAuthConfig = (oauthAction: TOAuthAction): TOAuthConfigs => {
  // query params
  const next_path = useSearchParams().get("next_path");
  // translation
  const { t } = useTranslation();
  // store hooks
  const { config } = useInstance();
  // derived values
  const providers = config?.oidc_providers ?? [];
  const getActionText = (provider: string): string => {
    if (oauthAction === "sign_up") return t("space_text.oauth.sign_up_with", { provider });
    if (oauthAction === "sign_in") return t("space_text.oauth.sign_in_with", { provider });
    return t("space_text.oauth.continue_with", { provider });
  };
  const renderIcon = (provider: TOidcProviderOption) => {
    const alt = t("app_text.integrations.logo_alt", { title: provider.name });
    if (provider.icon === "microsoft") return <img src={microsoftLogo} height={18} width={18} alt={alt} />;
    if (provider.icon === "google") return <img src={googleLogo} height={18} width={18} alt={alt} />;
    return <KeyOutline className="h-[18px] w-[18px] text-tertiary" />;
  };
  return {
    isOAuthEnabled: providers.length > 0,
    oAuthOptions: providers.map((provider) => ({
      id: provider.key,
      text: getActionText(provider.name),
      icon: renderIcon(provider),
      onClick: () => {
        window.location.assign(
          `${API_BASE_URL}/auth/spaces/oidc/${provider.key}/${next_path ? `?next_path=${next_path}` : ``}`
        );
      },
      enabled: true,
    })),
  };
};
