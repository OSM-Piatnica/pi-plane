/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getRelativeLuminance } from "../src/theme/color-conversion";
import { EDITOR_COLORS_DARK, EDITOR_COLORS_LIGHT } from "../src/theme/constants";
import { getStickyTextColors } from "../src/theme";

const cases = [
  { mode: "light", backgrounds: EDITOR_COLORS_LIGHT },
  { mode: "dark", backgrounds: EDITOR_COLORS_DARK },
] as const;

const getContrastRatio = (a: string, b: string): number => {
  const [lighter, darker] = [getRelativeLuminance(a), getRelativeLuminance(b)].toSorted((x, y) => y - x);
  return (lighter + 0.05) / (darker + 0.05);
};

describe("getStickyTextColors", () => {
  it("sets the same tokens in both modes", () => {
    expect(Object.keys(getStickyTextColors("light"))).toEqual(Object.keys(getStickyTextColors("dark")));
  });

  it.each(cases)("gives $mode stickies text that reads on every sticky colour (WCAG AA)", ({ mode, backgrounds }) => {
    const { "sticky-txt-primary": primary } = getStickyTextColors(mode);
    for (const background of Object.values(backgrounds)) {
      expect(getContrastRatio(primary, background)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it.each(cases)("keeps even $mode placeholder text visible on every sticky colour", ({ mode, backgrounds }) => {
    const { "sticky-txt-placeholder": placeholder } = getStickyTextColors(mode);
    for (const background of Object.values(backgrounds)) {
      expect(getContrastRatio(placeholder, background)).toBeGreaterThanOrEqual(3);
    }
  });
});
