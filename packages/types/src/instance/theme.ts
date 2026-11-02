/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** A colour theme every user of the instance can pick, next to the built-in ones. */
export type TInstanceTheme = {
  id: string;
  name: string;
  primary: string;
  background: string;
  dark_palette: boolean;
  /** semantic colour tokens (`bg-canvas`, `txt-primary`...) pinned to a hex colour */
  overrides: Record<string, string>;
  /** `deployment` themes come from the deployment and cannot be changed in the admin GUI */
  source: "deployment" | "admin";
  is_read_only: boolean;
};

export type TInstanceThemeCreate = Pick<TInstanceTheme, "name" | "primary" | "background" | "dark_palette"> & {
  overrides?: Record<string, string>;
};
