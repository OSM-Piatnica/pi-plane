/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import type { TOAuthConfigs } from "@plane/types";
// local imports
import type { TOAuthAction } from "./core";
import { useCoreOAuthConfig } from "./core";
import { useExtendedOAuthConfig } from "./extended";

export const useOAuthConfig = (oauthAction: TOAuthAction = "continue"): TOAuthConfigs => {
  const coreOAuthConfig = useCoreOAuthConfig(oauthAction);
  const extendedOAuthConfig = useExtendedOAuthConfig(oauthAction);
  return {
    isOAuthEnabled: coreOAuthConfig.isOAuthEnabled || extendedOAuthConfig.isOAuthEnabled,
    oAuthOptions: [...coreOAuthConfig.oAuthOptions, ...extendedOAuthConfig.oAuthOptions],
  };
};
