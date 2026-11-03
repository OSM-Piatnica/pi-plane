/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";

import { getDraggedWidth, getKeyResizedWidth, withoutColumnWidth } from "@/helpers/column-resize";

describe("getDraggedWidth", () => {
  it("follows the pointer", () => {
    expect(getDraggedWidth(200, 500, 560, 80)).toBe(260);
    expect(getDraggedWidth(200, 500, 450, 80)).toBe(150);
  });

  it("never goes below the minimum width", () => {
    expect(getDraggedWidth(200, 500, 100, 80)).toBe(80);
  });

  it("rounds to whole pixels", () => {
    expect(getDraggedWidth(200, 500, 500.6, 80)).toBe(201);
  });
});

describe("getKeyResizedWidth", () => {
  it("widens on the right arrow and narrows on the left one", () => {
    expect(getKeyResizedWidth(200, "ArrowRight", 80)).toBe(216);
    expect(getKeyResizedWidth(200, "ArrowLeft", 80)).toBe(184);
  });

  it("stops at the minimum width", () => {
    expect(getKeyResizedWidth(85, "ArrowLeft", 80)).toBe(80);
  });

  it("ignores other keys", () => {
    expect(getKeyResizedWidth(200, "Enter", 80)).toBeNull();
  });
});

describe("withoutColumnWidth", () => {
  it("drops one column and keeps the rest", () => {
    expect(withoutColumnWidth({ a: 100, b: 200 }, "a")).toEqual({ b: 200 });
  });

  it("leaves the widths alone when the column has none", () => {
    expect(withoutColumnWidth({ a: 100 }, "b")).toEqual({ a: 100 });
  });
});
