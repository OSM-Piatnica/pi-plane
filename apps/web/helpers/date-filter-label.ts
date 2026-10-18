/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { useTranslation } from "@plane/i18n";
import { capitalizeFirstLetter } from "@plane/utils";

type TTranslate = ReturnType<typeof useTranslation>["t"];

/**
 * The text of an applied date filter such as "After Jan 05, 2024", in the user's language.
 * @param date the date part of the stored filter value ("2024-01-01;after" -> "2024-01-01")
 * @param time the direction part of the stored filter value ("after" or "before"), kept in English in storage
 * @param formatDate formats the date for display
 * @param t translation function
 */
export const getDateFilterLabel = (
  date: string,
  time: string,
  formatDate: (date: string) => string | null | undefined,
  t: TTranslate
): string => {
  const formattedDate = formatDate(date) ?? "";
  if (time === "after") return t("date_phrases.after_date", { date: formattedDate });
  if (time === "before") return t("date_phrases.before_date", { date: formattedDate });
  return `${capitalizeFirstLetter(time)} ${formattedDate}`;
};
