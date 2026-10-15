/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export type TLanguage =
  | "en"
  | "fr"
  | "es"
  | "ja"
  | "zh-CN"
  | "zh-TW"
  | "ru"
  | "it"
  | "cs"
  | "sk"
  | "de"
  | "ua"
  | "pl"
  | "nl"
  | "ko"
  | "pt-BR"
  | "pt-PT"
  | "id"
  | "ro"
  | "vi-VN"
  | "tr-TR"
  | "ka-ge";

export interface ILanguageOption {
  label: string;
  value: TLanguage;
}
