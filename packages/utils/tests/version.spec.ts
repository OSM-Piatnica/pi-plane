/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { isNewerVersion } from "../src/version";

describe("isNewerVersion", () => {
  it("is true when the latest release is ahead", () => {
    expect(isNewerVersion("v1.3.1-pi.3", "1.3.1-pi.2")).toBe(true);
    expect(isNewerVersion("1.4.0", "1.3.9")).toBe(true);
    expect(isNewerVersion("1.10.0", "1.9.0")).toBe(true);
  });

  it("is false for the same release, however it is written", () => {
    expect(isNewerVersion("v1.3.1-pi.2", "1.3.1-pi.2")).toBe(false);
    expect(isNewerVersion("v1.3.1-pi.2", "1.3.1+pi.2")).toBe(false);
  });

  it("is false when the running version is ahead of the latest release", () => {
    expect(isNewerVersion("v1.3.1-pi.2", "1.3.1-pi.3")).toBe(false);
    expect(isNewerVersion("1.3.0", "1.3.1-pi.1")).toBe(false);
  });

  it("treats the longer version as newer when one is a prefix of the other", () => {
    expect(isNewerVersion("1.3.1-pi.2", "1.3.1")).toBe(true);
    expect(isNewerVersion("1.3.1", "1.3.1-pi.2")).toBe(false);
  });

  it("is false when either value is missing", () => {
    expect(isNewerVersion(undefined, "1.0.0")).toBe(false);
    expect(isNewerVersion("1.0.0", null)).toBe(false);
    expect(isNewerVersion("", "")).toBe(false);
  });
});
