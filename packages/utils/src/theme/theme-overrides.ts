/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Advanced custom theme: the semantic colour tokens the preset themes (light, dark, high contrast) set one by one,
 * which a custom theme can pin to a colour of its own on top of the palette generated from its two base colours.
 *
 * Tokens are named like the CSS variables in the design system (`bg-canvas` is `--bg-canvas`). Only the tokens listed
 * here can be set, so a saved or imported theme can never write anything else to the page's style.
 */

import { normalizeHexColor, validateHexColor } from "./color-validation";

export type TThemeOverrides = Record<string, string>;

export type TThemeOverrideToken = {
  /** name of the CSS variable without the leading `--` */
  token: string;
  /** translation key below `core_ui.theme.advanced.tokens` */
  labelKey: string;
};

export type TThemeOverrideGroup = {
  /** translation key below `core_ui.theme.advanced.groups` */
  key: string;
  tokens: TThemeOverrideToken[];
};

const statusTokens = (status: "info" | "success" | "warning" | "danger"): TThemeOverrideToken[] => [
  { token: `bg-${status}-primary`, labelKey: "status_solid" },
  { token: `bg-${status}-subtle`, labelKey: "status_subtle" },
  { token: `txt-${status}-primary`, labelKey: "status_text" },
  { token: `border-${status}-strong`, labelKey: "status_border" },
];

export const THEME_OVERRIDE_GROUPS: TThemeOverrideGroup[] = [
  {
    key: "backgrounds",
    tokens: [
      { token: "bg-canvas", labelKey: "canvas" },
      { token: "bg-surface-1", labelKey: "surface" },
      { token: "bg-surface-2", labelKey: "surface_secondary" },
      { token: "bg-layer-1", labelKey: "layer_1" },
      { token: "bg-layer-1-hover", labelKey: "layer_1_hover" },
      { token: "bg-layer-2", labelKey: "layer_2" },
      { token: "bg-layer-2-hover", labelKey: "layer_2_hover" },
      { token: "bg-layer-3", labelKey: "layer_3" },
      { token: "bg-inverse", labelKey: "inverse" },
    ],
  },
  {
    key: "accent",
    tokens: [
      { token: "bg-accent-primary", labelKey: "accent_solid" },
      { token: "bg-accent-primary-hover", labelKey: "accent_solid_hover" },
      { token: "bg-accent-subtle", labelKey: "accent_subtle" },
      { token: "border-accent-strong", labelKey: "accent_border_strong" },
      { token: "border-accent-subtle", labelKey: "accent_border_subtle" },
      { token: "txt-accent-primary", labelKey: "accent_text" },
      { token: "txt-accent-secondary", labelKey: "accent_text_secondary" },
      { token: "txt-link-primary", labelKey: "link" },
      { token: "txt-link-primary-hover", labelKey: "link_hover" },
      { token: "txt-on-color", labelKey: "on_accent" },
    ],
  },
  {
    key: "text",
    tokens: [
      { token: "txt-primary", labelKey: "text_primary" },
      { token: "txt-secondary", labelKey: "text_secondary" },
      { token: "txt-tertiary", labelKey: "text_tertiary" },
      { token: "txt-placeholder", labelKey: "text_placeholder" },
      { token: "txt-disabled", labelKey: "text_disabled" },
    ],
  },
  {
    key: "borders",
    tokens: [
      { token: "border-subtle", labelKey: "border_subtle" },
      { token: "border-subtle-1", labelKey: "border_subtle_strong" },
      { token: "border-strong", labelKey: "border_strong" },
      { token: "border-strong-1", labelKey: "border_strong_1" },
    ],
  },
  { key: "info", tokens: statusTokens("info") },
  { key: "success", tokens: statusTokens("success") },
  { key: "warning", tokens: statusTokens("warning") },
  { key: "danger", tokens: statusTokens("danger") },
];

export const THEME_OVERRIDE_TOKENS: readonly string[] = THEME_OVERRIDE_GROUPS.flatMap((group) =>
  group.tokens.map((entry) => entry.token)
);

const KNOWN_TOKENS = new Set(THEME_OVERRIDE_TOKENS);

/** `#abc`, `ABC` or `#AABBCC` as `#aabbcc` */
export const toOverrideHex = (value: string): string => `#${normalizeHexColor(value).toLowerCase()}`;

export type TSanitizedThemeOverrides = {
  overrides: TThemeOverrides;
  /** names that are not themeable tokens; they are dropped */
  unknown: string[];
  /** themeable tokens whose value is not a hex colour; they are dropped */
  invalid: string[];
};

/**
 * Reduces anything read from a saved profile or an imported file to the overrides that can safely be applied:
 * known token names with a hex colour, written as `#rrggbb`.
 */
export function sanitizeThemeOverrides(input: unknown): TSanitizedThemeOverrides {
  const result: TSanitizedThemeOverrides = { overrides: {}, unknown: [], invalid: [] };
  if (!input || typeof input !== "object" || Array.isArray(input)) return result;

  Object.entries(input as Record<string, unknown>).forEach(([token, value]) => {
    if (!KNOWN_TOKENS.has(token)) {
      result.unknown.push(token);
      return;
    }
    if (typeof value !== "string" || !validateHexColor(value)) {
      result.invalid.push(token);
      return;
    }
    result.overrides[token] = toOverrideHex(value);
  });
  return result;
}

/** Removes every themeable colour from the page, so the palette (or the preset theme) shows through again. */
export function clearThemeOverrides(): void {
  const themeElement = document?.querySelector("html");
  if (!themeElement) return;
  THEME_OVERRIDE_TOKENS.forEach((token) => themeElement.style.removeProperty(`--${token}`));
}

/** Pins the given tokens on the page; every other themeable token goes back to what the palette says. */
export function applyThemeOverrides(overrides: unknown): void {
  const themeElement = document?.querySelector("html");
  if (!themeElement) return;
  const { overrides: safe } = sanitizeThemeOverrides(overrides);
  THEME_OVERRIDE_TOKENS.forEach((token) => {
    const value = safe[token];
    if (value) themeElement.style.setProperty(`--${token}`, value);
    else themeElement.style.removeProperty(`--${token}`);
  });
}
