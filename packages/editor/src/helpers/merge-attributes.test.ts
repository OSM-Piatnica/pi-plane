/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { mergeAttributes } from "./merge-attributes";

describe("mergeAttributes", () => {
  it("merges attributes like @tiptap/core", () => {
    expect(mergeAttributes({ class: "a", id: "x" }, { class: "b", id: "y" })).toEqual({ class: "a b", id: "y" });
  });

  it("does not let an own __proto__ key set the prototype of the result", () => {
    const malicious = JSON.parse('{"__proto__": {"src": "x", "onerror": "alert(1)"}, "data-ok": "1"}');
    const result = mergeAttributes({ class: "a" }, malicious);

    expect(Object.getPrototypeOf(result)).toBe(Object.prototype);
    expect((result as Record<string, unknown>).onerror).toBeUndefined();
    expect("onerror" in result).toBe(false);
    expect(result).toEqual({ class: "a", "data-ok": "1" });
  });
});
