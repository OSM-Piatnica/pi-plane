/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { FALLBACK_LANGUAGE, SUPPORTED_LANGUAGES } from "../constants/language";
import type { TLanguage } from "../types";

// Browser language subtags whose app locale code differs from the BCP 47 tag.
const LANGUAGE_ALIASES: Record<string, TLanguage> = {
  uk: "ua",
  ka: "ka-ge",
  vi: "vi-VN",
  tr: "tr-TR",
  pt: "pt-BR",
  zh: "zh-CN",
  "zh-hans": "zh-CN",
  "zh-hant": "zh-TW",
  "zh-hk": "zh-TW",
  "zh-mo": "zh-TW",
};

// Locales that are chosen deliberately and never inferred from the system language.
const EXPLICIT_ONLY_LANGUAGES: TLanguage[] = new Set(["pl-x-podlaski"]);

const findSupported = (tag: string): TLanguage | undefined => {
  const lower = tag.toLowerCase();
  return SUPPORTED_LANGUAGES.map((language) => language.value).find(
    (value) => value.toLowerCase() === lower && !EXPLICIT_ONLY_LANGUAGES.has(value)
  );
};

// Tries the full tag, then ever shorter prefixes: zh-Hant-TW -> zh-Hant -> zh.
const matchTag = (tag: string): TLanguage | undefined => {
  const parts = tag.toLowerCase().replaceAll("_", "-").split("-");
  for (let length = parts.length; length > 0; length--) {
    const prefix = parts.slice(0, length).join("-");
    const match = findSupported(prefix) ?? LANGUAGE_ALIASES[prefix];
    if (match) return match;
  }
  return undefined;
};

/**
 * Picks the first supported locale from a list of browser language tags (most preferred first),
 * e.g. `["pl-PL", "en-US"]` -> `"pl"`. Returns the fallback language when none match.
 */
export const detectLanguage = (preferred: readonly string[] | undefined): TLanguage => {
  for (const tag of preferred ?? []) {
    const match = matchTag(tag);
    if (match) return match;
  }
  return FALLBACK_LANGUAGE;
};

/** The system language as reported by the browser, or the fallback outside a browser. */
export const getSystemLanguage = (): TLanguage => {
  if (typeof navigator === "undefined") return FALLBACK_LANGUAGE;
  return detectLanguage(navigator.languages?.length ? navigator.languages : [navigator.language]);
};
