/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { sanitizeThemeOverrides, toOverrideHex, validateHexColor } from "@plane/utils";

/** Reads a theme file: the config the app exports from Appearance (`themeName`, `primary`, `background`, ...). */
export const parseThemeFile = async (file: File) => {
  const raw = JSON.parse(await file.text()) as Record<string, unknown>;
  const primary = String(raw.primary ?? "");
  const background = String(raw.background ?? "");
  if (!validateHexColor(primary) || !validateHexColor(background)) {
    throw new Error("The file needs a primary and a background colour, written as hex codes like #4F8F7D.");
  }
  const { overrides, invalid } = sanitizeThemeOverrides(raw.overrides);
  if (invalid.length > 0) throw new Error(`These colours are not hex codes: ${invalid.join(", ")}.`);
  const name = String(raw.themeName ?? raw.name ?? file.name.replace(/\.json$/i, "")).trim();
  return {
    name,
    primary: toOverrideHex(primary),
    background: toOverrideHex(background),
    dark_palette: raw.darkPalette === true,
    overrides,
  };
};

/** The first readable message of a failed call: our own error, or the first field the API complained about. */
export const getThemeErrorMessage = (error: unknown) => {
  if (error instanceof Error) return error.message;
  if (error && typeof error === "object") {
    const found = Object.values(error).find((value) => typeof value === "string");
    if (found) return found;
  }
  return "Something went wrong.";
};
