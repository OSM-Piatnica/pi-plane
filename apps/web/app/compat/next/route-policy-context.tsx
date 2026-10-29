/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the default workspace short links of Hangar (szymczag/hangar, AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { normalizeDefaultWorkspacePath } from "./route-policy";

type TRoutePolicy = {
  /** Slug of the workspace the instance chose for short links, once it is known. */
  defaultWorkspaceSlug?: string;
  normalizePath: (path: string) => string;
};

const RoutePolicyContext = createContext<TRoutePolicy>({
  normalizePath: (path) => path,
});

type TRoutePolicyProviderProps = {
  children: ReactNode;
  defaultWorkspaceSlug?: string;
};

export function RoutePolicyProvider({ children, defaultWorkspaceSlug }: TRoutePolicyProviderProps) {
  const value = useMemo<TRoutePolicy>(
    () => ({
      defaultWorkspaceSlug,
      normalizePath: (path) => normalizeDefaultWorkspacePath(path, defaultWorkspaceSlug),
    }),
    [defaultWorkspaceSlug]
  );

  return <RoutePolicyContext.Provider value={value}>{children}</RoutePolicyContext.Provider>;
}

export const useRoutePolicy = () => useContext(RoutePolicyContext);
