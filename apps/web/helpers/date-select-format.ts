/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// English keeps the app's usual "Jan 05, 2024"; other languages use date-fns' localized medium date ("5. Jan. 2024"),
// which puts the day, month and year in that language's order (the same rule as `useLocalizedDates`).
const ENGLISH_LOCALE_CODE = "en-US";
const LOCALIZED_DATE_TOKEN = "PP";

/** The trigger date style of a language: `undefined` keeps the blocks' English default. */
export const getDateSelectFormatToken = (localeCode: string | undefined) =>
  localeCode === ENGLISH_LOCALE_CODE ? undefined : LOCALIZED_DATE_TOKEN;
