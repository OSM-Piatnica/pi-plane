/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
import type { Locale } from "date-fns";
import { cs, de, enUS, es, fr, id, it, ja, ka, ko, pl, ptBR, ro, ru, sk, tr, uk, vi, zhCN, zhTW } from "date-fns/locale";
// plane imports
import type { TLanguage } from "@plane/i18n";
import { useTranslation } from "@plane/i18n";
import type { EStartOfTheWeek } from "@plane/types";

// BCP 47 tags understood by Intl for every language supported by the app
const INTL_LOCALES: Record<TLanguage, string> = {
  en: "en-US",
  fr: "fr",
  es: "es",
  ja: "ja",
  "zh-CN": "zh-CN",
  "zh-TW": "zh-TW",
  ru: "ru",
  it: "it",
  cs: "cs",
  sk: "sk",
  de: "de",
  ua: "uk",
  pl: "pl",
  ko: "ko",
  "pt-BR": "pt-BR",
  id: "id",
  ro: "ro",
  "vi-VN": "vi",
  "tr-TR": "tr",
  "ka-ge": "ka",
};

// date-fns locales, used by the date pickers (react-day-picker)
const DATE_FNS_LOCALES: Record<TLanguage, Locale> = {
  en: enUS,
  fr,
  es,
  ja,
  "zh-CN": zhCN,
  "zh-TW": zhTW,
  ru,
  it,
  cs,
  sk,
  de,
  ua: uk,
  pl,
  ko,
  "pt-BR": ptBR,
  id,
  ro,
  "vi-VN": vi,
  "tr-TR": tr,
  "ka-ge": ka,
};

const capitalize = (value: string, locale: string) =>
  value.charAt(0).toLocaleUpperCase(locale) + value.slice(1);

/**
 * Localized calendar helpers (month names, weekday names, date picker locale) for the user's current language.
 */
export const useCalendarLocale = () => {
  const { currentLocale } = useTranslation();
  const intlLocale = INTL_LOCALES[currentLocale] ?? INTL_LOCALES.en;
  const dateFnsLocale = DATE_FNS_LOCALES[currentLocale] ?? enUS;

  const getMonthName = useCallback(
    (monthNumber: number, style: "long" | "short" = "long") =>
      // month is 1-indexed, the day is fixed to avoid overflow into the next month
      capitalize(
        new Intl.DateTimeFormat(intlLocale, { month: style, timeZone: "UTC" }).format(
          new Date(Date.UTC(2024, monthNumber - 1, 1))
        ),
        intlLocale
      ),
    [intlLocale]
  );

  const getWeekdayName = useCallback(
    (day: EStartOfTheWeek, style: "long" | "short" = "long") =>
      // 2024-01-07 is a Sunday, so 0 (Sunday) .. 6 (Saturday) maps directly
      capitalize(
        new Intl.DateTimeFormat(intlLocale, { weekday: style, timeZone: "UTC" }).format(
          new Date(Date.UTC(2024, 0, 7 + day))
        ),
        intlLocale
      ),
    [intlLocale]
  );

  return useMemo(
    () => ({ intlLocale, dateFnsLocale, getMonthName, getWeekdayName }),
    [intlLocale, dateFnsLocale, getMonthName, getWeekdayName]
  );
};
