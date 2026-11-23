/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getWorkItemTypeMarkKind, hasLogo } from "@/helpers/work-item-type-mark";

describe("hasLogo", () => {
  it("is true for an emoji or an icon that names something", () => {
    expect(hasLogo({ in_use: "emoji", emoji: { value: "128640" } })).toBe(true);
    expect(hasLogo({ in_use: "icon", icon: { name: "rocket", color: "#6d28d9" } })).toBe(true);
  });

  it("is false for no logo, an empty one, or one whose chosen kind is empty", () => {
    expect(hasLogo(undefined)).toBe(false);
    expect(hasLogo(null)).toBe(false);
    expect(hasLogo({})).toBe(false);
    expect(hasLogo({ in_use: "emoji", emoji: {} })).toBe(false);
    expect(hasLogo({ in_use: "icon", icon: { name: "" } })).toBe(false);
    // only the kind in use counts
    expect(hasLogo({ in_use: "emoji", icon: { name: "rocket" } })).toBe(false);
  });
});

describe("getWorkItemTypeMarkKind", () => {
  const logo = { in_use: "icon", icon: { name: "rocket" } } as const;

  it("prefers the logo an admin picked, also on an Epic type", () => {
    expect(getWorkItemTypeMarkKind({ logo_props: logo, is_epic: false })).toBe("logo");
    expect(getWorkItemTypeMarkKind({ logo_props: logo, is_epic: true })).toBe("logo");
  });

  it("falls back to a built-in mark for Epics, and a general one for the rest", () => {
    expect(getWorkItemTypeMarkKind({ logo_props: {} as never, is_epic: true })).toBe("epic");
    expect(getWorkItemTypeMarkKind({ logo_props: {} as never, is_epic: false })).toBe("default");
  });
});
