/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  applyThemeOverrides,
  clearThemeOverrides,
  sanitizeThemeOverrides,
  THEME_OVERRIDE_GROUPS,
  THEME_OVERRIDE_TOKENS,
} from "../src/theme";

describe("theme override tokens", () => {
  it("lists every token once", () => {
    expect(new Set(THEME_OVERRIDE_TOKENS).size).toBe(THEME_OVERRIDE_TOKENS.length);
    expect(THEME_OVERRIDE_GROUPS.every((group) => group.tokens.length > 0)).toBe(true);
  });
});

describe("sanitizeThemeOverrides", () => {
  it("keeps known tokens with a hex colour and writes them as #rrggbb", () => {
    const { overrides, unknown, invalid } = sanitizeThemeOverrides({
      "bg-canvas": "#ABC",
      "txt-primary": "112233",
      "border-subtle": "#AABBCC",
    });
    expect(overrides).toEqual({ "bg-canvas": "#aabbcc", "txt-primary": "#112233", "border-subtle": "#aabbcc" });
    expect(unknown).toEqual([]);
    expect(invalid).toEqual([]);
  });

  it("drops names that are not themeable and reports them", () => {
    const { overrides, unknown } = sanitizeThemeOverrides({
      "bg-canvas": "#ffffff",
      "--evil": "#000000",
      position: "#111",
    });
    expect(overrides).toEqual({ "bg-canvas": "#ffffff" });
    expect(unknown).toEqual(["--evil", "position"]);
  });

  it("drops values that are not a hex colour and reports their token", () => {
    const { overrides, invalid } = sanitizeThemeOverrides({
      "bg-canvas": "red",
      "txt-primary": "url(javascript:alert(1))",
      "border-strong": 12,
      "bg-surface-1": "#12345",
      "bg-layer-1": "#fff",
    });
    expect(overrides).toEqual({ "bg-layer-1": "#ffffff" });
    expect(invalid).toEqual(["bg-canvas", "txt-primary", "border-strong", "bg-surface-1"]);
  });

  it.each([undefined, null, "bg-canvas", 5, ["bg-canvas"]])("returns nothing for %j", (input) => {
    expect(sanitizeThemeOverrides(input)).toEqual({ overrides: {}, unknown: [], invalid: [] });
  });
});

describe("applying overrides to the page", () => {
  const style = new Map<string, string>();
  const original = (globalThis as { document?: unknown }).document;

  beforeEach(() => {
    style.clear();
    (globalThis as { document?: unknown }).document = {
      querySelector: () => ({
        style: {
          setProperty: (name: string, value: string) => style.set(name, value),
          removeProperty: (name: string) => style.delete(name),
        },
      }),
    };
  });

  afterEach(() => {
    (globalThis as { document?: unknown }).document = original;
  });

  it("sets the given tokens as CSS variables and nothing else", () => {
    applyThemeOverrides({ "bg-canvas": "#101010", "--other": "#ffffff", "txt-primary": "nope" });
    expect([...style.entries()]).toEqual([["--bg-canvas", "#101010"]]);
  });

  it("removes tokens that are no longer given", () => {
    applyThemeOverrides({ "bg-canvas": "#101010", "txt-primary": "#eeeeee" });
    applyThemeOverrides({ "txt-primary": "#eeeeee" });
    expect([...style.keys()]).toEqual(["--txt-primary"]);
  });

  it("clears every token", () => {
    applyThemeOverrides({ "bg-canvas": "#101010", "txt-primary": "#eeeeee" });
    clearThemeOverrides();
    expect(style.size).toBe(0);
  });
});
