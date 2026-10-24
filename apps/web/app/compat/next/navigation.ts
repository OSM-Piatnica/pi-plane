/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import { useLocation, useNavigate, useParams as useParamsRR, useSearchParams as useSearchParamsRR } from "react-router";
import { ensureTrailingSlash } from "./helper";
import { withDefaultWorkspaceParams } from "./route-policy";
import { useRoutePolicy } from "./route-policy-context";

export function useRouter() {
  const navigate = useNavigate();
  const { normalizePath } = useRoutePolicy();
  return useMemo(
    () => ({
      push: (to: string) => {
        // Defer navigation to avoid state updates during render
        setTimeout(() => navigate(ensureTrailingSlash(normalizePath(to))), 0);
      },
      replace: (to: string) => {
        // Defer navigation to avoid state updates during render
        setTimeout(() => navigate(ensureTrailingSlash(normalizePath(to)), { replace: true }), 0);
      },
      back: () => {
        setTimeout(() => navigate(-1), 0);
      },
      forward: () => {
        setTimeout(() => navigate(1), 0);
      },
      refresh: () => {
        location.reload();
      },
      prefetch: async (_to: string) => {
        // no-op in this shim
      },
    }),
    [navigate, normalizePath]
  );
}

export function usePathname(): string {
  const { pathname } = useLocation();
  return pathname;
}

export function useSearchParams(): URLSearchParams {
  const [searchParams] = useSearchParamsRR();
  return searchParams;
}

export function useParams(): Readonly<Record<string, string>> {
  const params = useParamsRR();
  const { defaultWorkspaceSlug } = useRoutePolicy();
  return useMemo(
    () => withDefaultWorkspaceParams(params, defaultWorkspaceSlug) as Readonly<Record<string, string>>,
    [params, defaultWorkspaceSlug]
  );
}
