/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { sanitizePinnedKeys, togglePinnedKey } from "@/components/common/layout/sidebar/pinned-properties";

describe("togglePinnedKey", () => {
  it("pins a property that is not pinned yet", () => {
    expect(togglePinnedKey(["state"], "priority")).toEqual(["state", "priority"]);
  });

  it("unpins a property that is pinned, keeping the others", () => {
    expect(togglePinnedKey(["state", "priority", "labels"], "priority")).toEqual(["state", "labels"]);
  });

  it("does not mutate the stored list", () => {
    const pinned = ["state"];
    togglePinnedKey(pinned, "priority");
    expect(pinned).toEqual(["state"]);
  });
});

describe("sanitizePinnedKeys", () => {
  it("keeps a list of strings", () => {
    expect(sanitizePinnedKeys(["state", "custom_1"])).toEqual(["state", "custom_1"]);
  });

  it("drops entries that are not strings", () => {
    expect(sanitizePinnedKeys(["state", 1, null, { a: 1 }])).toEqual(["state"]);
  });

  it("falls back to no pins for anything that is not a list", () => {
    expect(sanitizePinnedKeys(null)).toEqual([]);
    expect(sanitizePinnedKeys("state")).toEqual([]);
    expect(sanitizePinnedKeys({ state: true })).toEqual([]);
  });
});
