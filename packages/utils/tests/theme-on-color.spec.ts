/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getOnColorTextColors } from "../src/theme/theme-application";

const WHITE = { l: 1, c: 0, h: 0 };
const BLACK = { l: 0, c: 0, h: 0 };

describe("getOnColorTextColors", () => {
  it.each(["#3f76ff", "#22c55e", "#dc2626", "#7c3aed", "#0f172a", "#000000"])(
    "gives white text and a white icon on the dark accent %s",
    (accent) => {
      expect(getOnColorTextColors(accent)).toEqual({ textColor: WHITE, iconColor: WHITE });
    }
  );

  it.each(["#f5c518", "#ffff00", "#ffffff", "#fde68a"])(
    "gives black text and a black icon on the light accent %s",
    (accent) => {
      expect(getOnColorTextColors(accent)).toEqual({ textColor: BLACK, iconColor: BLACK });
    }
  );

  it("never gives the icon the opposite of the text, whatever the detection method", () => {
    for (const method of ["wcag", "oklch", "perceptual"] as const) {
      for (const accent of ["#3f76ff", "#f5c518", "#22c55e", "#dc2626", "#808080"]) {
        const { textColor, iconColor } = getOnColorTextColors(accent, method);
        expect(iconColor).toEqual(textColor);
      }
    }
  });
});
