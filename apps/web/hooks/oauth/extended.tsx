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
import type { TOAuthConfigs, TOidcProviderOption } from "@plane/types";
// assets
import googleLogo from "@/app/assets/logos/google-logo.svg?url";
import microsoftLogo from "@/app/assets/logos/microsoft-logo.svg?url";
// hooks
import { useInstance } from "@/hooks/store/use-instance";

const renderOidcIcon = (provider: TOidcProviderOption) => {
  if (provider.icon === "microsoft")
    return <img src={microsoftLogo} height={18} width={18} alt={`${provider.name} Logo`} />;
  if (provider.icon === "google") return <img src={googleLogo} height={18} width={18} alt={`${provider.name} Logo`} />;
  return <KeyOutline className="h-[18px] w-[18px] text-tertiary" />;
};

/** The single sign-on providers (OpenID Connect) that the server lists as configured. */
export const useExtendedOAuthConfig = (oauthActionText: string): TOAuthConfigs => {
  // query params
  const next_path = useSearchParams().get("next_path");
  // store hooks
  const { config } = useInstance();
  // derived values
  const providers = config?.oidc_providers ?? [];
  return {
    isOAuthEnabled: providers.length > 0,
    oAuthOptions: providers.map((provider) => ({
      id: provider.key,
      text: `${oauthActionText} with ${provider.name}`,
      icon: renderOidcIcon(provider),
      onClick: () => {
        window.location.assign(
          `${API_BASE_URL}/auth/oidc/${provider.key}/${next_path ? `?next_path=${next_path}` : ``}`
        );
      },
      enabled: true,
    })),
  };
};
