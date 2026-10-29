/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { SUPPORTED_LANGUAGES } from "../src/constants/language";
import { detectLanguage } from "../src/core/detect-language";

describe("detectLanguage", () => {
  it("matches a region tag to its base locale", () => {
    expect(detectLanguage(["pl-PL"])).toBe("pl");
    expect(detectLanguage(["de-AT"])).toBe("de");
    expect(detectLanguage(["en-GB"])).toBe("en");
  });

  it("prefers an exact regional locale over its base", () => {
    expect(detectLanguage(["pt-PT"])).toBe("pt-PT");
    expect(detectLanguage(["pt-BR"])).toBe("pt-BR");
    expect(detectLanguage(["zh-TW"])).toBe("zh-TW");
  });

  it("maps tags whose app code differs from the BCP 47 tag", () => {
    expect(detectLanguage(["uk-UA"])).toBe("ua");
    expect(detectLanguage(["ka"])).toBe("ka-ge");
    expect(detectLanguage(["vi"])).toBe("vi-VN");
    expect(detectLanguage(["pt"])).toBe("pt-BR");
    expect(detectLanguage(["zh"])).toBe("zh-CN");
    expect(detectLanguage(["zh-Hant-TW"])).toBe("zh-TW");
    expect(detectLanguage(["zh-Hans-CN"])).toBe("zh-CN");
  });

  it("takes the first supported language in preference order", () => {
    expect(detectLanguage(["xx", "fr-CA", "pl"])).toBe("fr");
  });

  it("falls back to English when nothing matches or nothing is given", () => {
    expect(detectLanguage(["xx-YY"])).toBe("en");
    expect(detectLanguage([])).toBe("en");
    expect(detectLanguage(undefined)).toBe("en");
  });

  it("never infers the Podlaski locale", () => {
    expect(detectLanguage(["pl-x-podlaski"])).toBe("pl");
  });

  it("only ever returns a supported locale", () => {
    const supported = SUPPORTED_LANGUAGES.map((language) => language.value);
    for (const tag of ["en-US", "pl-PL", "uk", "zh-HK", "nb-NO", "pt", "ja-JP"]) {
      expect(supported).toContain(detectLanguage([tag]));
    }
  });
});
