/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TInstanceTheme } from "@plane/types";

/**
 * Where a saved custom theme came from.
 *
 * Picking an instance theme saves it as the user's custom theme together with the id it came from. While that link
 * points at an instance theme that still exists, the theme is managed by the administrator and the custom theme editor
 * stays out of the way: its mode switch and colour fields would only fight the colours the theme pins.
 */
export type TInstanceThemeLink =
  /** the user's own custom theme, or an instance theme that was deleted since: the editor applies */
  | { status: "own" }
  /** the instance themes are still loading: show neither the editor nor the notice yet */
  | { status: "loading" }
  /** an instance theme that exists: read only */
  | { status: "managed"; name: string };

export const getInstanceThemeLink = (props: {
  instanceThemeId: string | undefined;
  instanceThemes: TInstanceTheme[] | undefined;
  /** the instance themes could not be loaded */
  hasFailed?: boolean;
}): TInstanceThemeLink => {
  const { instanceThemeId, instanceThemes, hasFailed = false } = props;
  if (!instanceThemeId) return { status: "own" };
  if (!instanceThemes) return hasFailed ? { status: "own" } : { status: "loading" };
  const instanceTheme = instanceThemes.find((theme) => theme.id === instanceThemeId);
  return instanceTheme ? { status: "managed", name: instanceTheme.name } : { status: "own" };
};
