/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Route of the workspace home, or the root route (which redirects to the user's workspace) when no workspace is known.
 */
export const getWorkspaceHomeHref = (workspaceSlug?: string): string => (workspaceSlug ? `/${workspaceSlug}/` : "/");

/**
 * Whether the browser has an earlier history entry to return to. A page opened directly (new tab, shared link)
 * has only its own entry, so going back would leave the app or do nothing.
 */
export const canGoBackInHistory = (historyLength: number): boolean => historyLength > 1;
