/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { validateOptionalPersonName, validatePersonName } from "../src/validation";

const t = (key: string) => `translated:${key}`;

describe("validateOptionalPersonName", () => {
  it("accepts an empty, blank or missing name", () => {
    expect(validateOptionalPersonName("")).toBe(true);
    expect(validateOptionalPersonName("   ")).toBe(true);
    expect(validateOptionalPersonName(undefined)).toBe(true);
  });

  it("accepts a valid name", () => {
    expect(validateOptionalPersonName("Kranzberg")).toBe(true);
    expect(validateOptionalPersonName("Jean-Paul")).toBe(true);
  });

  it("still rejects a name with blocked characters", () => {
    expect(validateOptionalPersonName("John<script>")).not.toBe(true);
  });

  it("passes the translate function on to the message", () => {
    expect(validateOptionalPersonName("John<script>", t)).toMatch(/^translated:/);
  });

  it("leaves the required validator strict", () => {
    expect(validatePersonName("")).not.toBe(true);
  });
});
