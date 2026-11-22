/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  SHAREPOINT_DEFAULT_MAX_FILE_SIZE,
  SHAREPOINT_MAX_MAX_FILE_SIZE,
  bytesToMegabytesText,
  getSharePointMaxFileSize,
  megabytesTextToBytes,
  parseSharePointMaxFileSize,
  sharePointMaxFileSizeToSave,
} from "../src/sharepoint-file-size";

const MB = 1024 * 1024;

describe("getSharePointMaxFileSize", () => {
  it("applies a saved size in range", () => {
    expect(getSharePointMaxFileSize(String(200 * MB))).toEqual({
      applied: 200 * MB,
      isDefault: false,
      ignoredValue: undefined,
    });
    expect(getSharePointMaxFileSize("1000000000").applied).toBe(1000000000);
  });

  it("applies the default of 500 MB when nothing is saved", () => {
    for (const raw of [undefined, null, "", "  "]) {
      expect(getSharePointMaxFileSize(raw)).toEqual({
        applied: SHAREPOINT_DEFAULT_MAX_FILE_SIZE,
        isDefault: true,
        ignoredValue: undefined,
      });
    }
    expect(SHAREPOINT_DEFAULT_MAX_FILE_SIZE).toBe(500 * MB);
  });

  it("says which saved value it ignores, as the API does, and that the default applies instead", () => {
    for (const raw of ["12", String(MB - 1), String(SHAREPOINT_MAX_MAX_FILE_SIZE + 1), "lots", "1.5", "-5"]) {
      expect(getSharePointMaxFileSize(raw)).toEqual({
        applied: SHAREPOINT_DEFAULT_MAX_FILE_SIZE,
        isDefault: true,
        ignoredValue: raw,
      });
    }
  });

  it("accepts the bounds", () => {
    expect(parseSharePointMaxFileSize(String(MB))).toBe(MB);
    expect(parseSharePointMaxFileSize(String(SHAREPOINT_MAX_MAX_FILE_SIZE))).toBe(SHAREPOINT_MAX_MAX_FILE_SIZE);
  });
});

describe("bytes and megabytes in the field", () => {
  it("shows a whole number of megabytes as such", () => {
    expect(bytesToMegabytesText(500 * MB)).toBe("500");
    expect(bytesToMegabytesText(MB)).toBe("1");
  });

  it("shows a size that is not a whole number of megabytes faithfully, not rounded", () => {
    expect(bytesToMegabytesText(1000000000)).toBe("953.67431640625");
    // The shortest text that still converts back to exactly these bytes (see the round trip below)
    expect(bytesToMegabytesText(MB + 1)).toBe("1.0000009536743164");
  });

  it("turns what it shows back into the same bytes", () => {
    for (const bytes of [MB, MB + 1, 1000000000, 524288001, SHAREPOINT_MAX_MAX_FILE_SIZE - 1]) {
      expect(megabytesTextToBytes(bytesToMegabytesText(bytes))).toBe(bytes);
      expect(sharePointMaxFileSizeToSave(bytesToMegabytesText(bytes))).toBe(String(bytes));
    }
  });

  it("reads typed megabytes as whole bytes", () => {
    expect(megabytesTextToBytes("200")).toBe(200 * MB);
    expect(megabytesTextToBytes(" 1.5 ")).toBe(1.5 * MB);
    for (const text of ["", "abc", "-5", "1e3", "0", "1,5", "0x10"]) {
      expect(megabytesTextToBytes(text)).toBeUndefined();
    }
  });

  it("saves empty as empty (the default), refuses what the API would refuse", () => {
    expect(sharePointMaxFileSizeToSave("")).toBe("");
    expect(sharePointMaxFileSizeToSave("  ")).toBe("");
    expect(sharePointMaxFileSizeToSave("200")).toBe(String(200 * MB));
    expect(sharePointMaxFileSizeToSave("0.5")).toBeUndefined();
    expect(sharePointMaxFileSizeToSave(String(250 * 1024 + 1))).toBeUndefined();
    expect(sharePointMaxFileSizeToSave(String(250 * 1024))).toBe(String(SHAREPOINT_MAX_MAX_FILE_SIZE));
    expect(sharePointMaxFileSizeToSave("lots")).toBeUndefined();
  });
});
