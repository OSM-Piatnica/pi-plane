/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { CHART_COLOR_PALETTES } from "@plane/constants";
import { getBarColor, getWorkItemKeyColor } from "../../components/issues/issue-layouts/gantt/bar-color";
import { getChartPalette } from "../../lib/chart-palette";

const palette = CHART_COLOR_PALETTES[0]?.light ?? [];

describe("getWorkItemKeyColor", () => {
  it("is deterministic", () => {
    expect(getWorkItemKeyColor("FOO", 42, palette)).toBe(getWorkItemKeyColor("FOO", 42, palette));
  });

  it("gives consecutive keys different colours", () => {
    for (let sequenceId = 1; sequenceId < 50; sequenceId++) {
      expect(getWorkItemKeyColor("FOO", sequenceId, palette)).not.toBe(
        getWorkItemKeyColor("FOO", sequenceId + 1, palette)
      );
    }
  });

  it("uses every palette colour across a run of keys", () => {
    const colors = new Set(
      Array.from({ length: palette.length }, (_, i) => getWorkItemKeyColor("FOO", i + 1, palette))
    );
    expect(colors.size).toBe(palette.length);
  });

  it("wraps around the palette by sequence id", () => {
    expect(getWorkItemKeyColor("FOO", 3, palette)).toBe(getWorkItemKeyColor("FOO", 3 + palette.length, palette));
  });

  it("only returns palette colours", () => {
    for (const identifier of ["FOO", "BAR", "", "A-VERY-LONG-PROJECT-IDENTIFIER"]) {
      expect(palette).toContain(getWorkItemKeyColor(identifier, 7, palette));
    }
  });

  it("returns nothing without a sequence id or palette", () => {
    expect(getWorkItemKeyColor("FOO", undefined, palette)).toBeUndefined();
    expect(getWorkItemKeyColor("FOO", 1, [])).toBeUndefined();
  });
});

describe("getBarColor", () => {
  const base = { stateColor: "#123456", projectIdentifier: "FOO", palette };

  it("uses the state colour by default", () => {
    expect(getBarColor({ ...base, colorBy: undefined, sequenceId: 7 })).toBe("#123456");
    expect(getBarColor({ ...base, colorBy: "state", sequenceId: 7 })).toBe("#123456");
  });

  it("uses the key colour in key mode", () => {
    expect(getBarColor({ ...base, colorBy: "key", sequenceId: 7 })).toBe(getWorkItemKeyColor("FOO", 7, palette));
  });

  it("falls back to the state colour without a sequence id", () => {
    expect(getBarColor({ ...base, colorBy: "key", sequenceId: undefined })).toBe("#123456");
  });
});

describe("getChartPalette", () => {
  it("is the light palette for a light theme and the dark one for a dark theme", () => {
    expect(getChartPalette("light")).toEqual(CHART_COLOR_PALETTES[0]?.light);
    expect(getChartPalette("dark")).toEqual(CHART_COLOR_PALETTES[0]?.dark);
  });

  it("follows the profile for a custom theme", () => {
    expect(getChartPalette("custom", true)).toEqual(CHART_COLOR_PALETTES[0]?.dark);
    expect(getChartPalette("custom", false)).toEqual(CHART_COLOR_PALETTES[0]?.light);
  });
});
