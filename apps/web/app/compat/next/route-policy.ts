/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the default workspace short links of Hangar (szymczag/hangar, AGPL-3.0-only).
 * See the LICENSE file for details.
 */

type TRouteParams = Readonly<Record<string, string | undefined>>;

/**
 * Shortens `/<default-workspace>/browse/PROJ-1` to `/i/PROJ-1`; every other path is returned as it came.
 * Only canonical work item browse routes are shortened, so project, settings and archive links keep
 * their workspace slug.
 */
export const normalizeDefaultWorkspacePath = (path: string, workspaceSlug?: string): string => {
  if (!workspaceSlug || !path.startsWith("/")) return path;

  const suffixStart = path.search(/[?#]/u);
  const pathname = suffixStart === -1 ? path : path.slice(0, suffixStart);
  const suffix = suffixStart === -1 ? "" : path.slice(suffixStart);
  const escapedSlug = workspaceSlug.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
  const match = pathname.match(new RegExp(`^/${escapedSlug}/browse/([^/]+)/?$`, "u"));
  return match ? `/i/${match[1]}${suffix}` : path;
};

/**
 * The `/i/:workItem` route has no workspace segment, so the workspace the instance chose for short
 * links is supplied wherever a component asks for the `workspaceSlug` route param.
 */
export const withDefaultWorkspaceParams = (params: TRouteParams, defaultWorkspaceSlug?: string): TRouteParams =>
  params.workItem && !params.workspaceSlug && defaultWorkspaceSlug
    ? { ...params, workspaceSlug: defaultWorkspaceSlug }
    : params;
