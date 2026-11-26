/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TInstanceTheme } from "@plane/types";
import { getInstanceThemeLink, toInstanceThemesError } from "@/components/core/theme/instance-theme-link";

const theme = (id: string, name: string): TInstanceTheme => ({
  id,
  name,
  primary: "#4f8f7d",
  background: "#f3f5f4",
  dark_palette: false,
  overrides: {},
  source: "admin",
  is_read_only: false,
});

const themes = [theme("a", "Piątnica Light"), theme("b", "Piątnica Dark")];

describe("getInstanceThemeLink", () => {
  it("is the user's own theme when it never came from an instance theme", () => {
    expect(getInstanceThemeLink({ instanceThemeId: undefined, instanceThemes: themes })).toEqual({ status: "own" });
    expect(getInstanceThemeLink({ instanceThemeId: undefined, instanceThemes: undefined })).toEqual({ status: "own" });
  });

  it("is managed, with the theme's name, while the instance theme exists", () => {
    expect(getInstanceThemeLink({ instanceThemeId: "b", instanceThemes: themes })).toEqual({
      status: "managed",
      name: "Piątnica Dark",
    });
  });

  it("waits for the instance themes instead of flashing the editor", () => {
    expect(getInstanceThemeLink({ instanceThemeId: "a", instanceThemes: undefined })).toEqual({ status: "loading" });
  });

  it("opens the editor when the instance themes cannot be loaded", () => {
    expect(getInstanceThemeLink({ instanceThemeId: "a", instanceThemes: undefined, hasFailed: true })).toEqual({
      status: "own",
    });
  });

  it("opens the editor when the instance theme was deleted since", () => {
    expect(getInstanceThemeLink({ instanceThemeId: "gone", instanceThemes: themes })).toEqual({ status: "own" });
  });
});

describe("toInstanceThemesError", () => {
  it.each([undefined, null, ""])("turns a failure without a body (%j) into a real error, so SWR reports it", (body) => {
    expect(toInstanceThemesError(body)).toBeInstanceOf(Error);
  });

  it("passes a real error body on unchanged", () => {
    const body = { error: "Authentication credentials were not provided" };
    expect(toInstanceThemesError(body)).toBe(body);
    expect(toInstanceThemesError("Server error")).toBe("Server error");
  });
});
