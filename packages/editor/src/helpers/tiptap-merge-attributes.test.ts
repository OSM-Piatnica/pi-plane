/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Regression guard for GHSA-cp6q-959q-f8rh: Tiptap < 3.30.4 let an own `__proto__` key replace the prototype of the
// merged attributes. The editor used a wrapper until it moved to Tiptap 3; this keeps the upstream fix honest.
import { mergeAttributes } from "@tiptap/core";
import { expect, it } from "vitest";
it("v3 core ignores an own __proto__ key", () => {
  const evil = JSON.parse('{"__proto__": {"onerror": "alert(1)", "src": "x"}, "class": "a"}');
  const merged = mergeAttributes({ class: "b" }, evil);
  expect((merged as any).onerror).toBeUndefined();
  expect((merged as any).src).toBeUndefined();
  expect(Object.getPrototypeOf(merged)).toBe(Object.prototype);
});
