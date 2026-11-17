/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

const MB = 1024 * 1024;

/** What applies while the administrator has saved no size. */
export const DEFAULT_MAX_FILE_SIZE_MB = 500;
/** What SharePoint Online itself takes for one file (250 GB). */
export const MAX_MAX_FILE_SIZE_MB = 250 * 1024;

/** The saved size (bytes, as text) in megabytes for the form; empty when nothing usable is saved. */
export const bytesToMegabytes = (bytes: string | undefined): string => {
  const amount = Number(bytes);
  if (!bytes || !Number.isFinite(amount) || amount <= 0) return "";
  return String(Math.max(1, Math.round(amount / MB)));
};

/** Whether the text is a size in whole megabytes that can be saved; empty is fine (the default applies). */
export const isValidMegabytes = (megabytes: string): boolean => {
  const text = megabytes.trim();
  if (text === "") return true;
  const amount = Number(text);
  return /^\d+$/.test(text) && amount >= 1 && amount <= MAX_MAX_FILE_SIZE_MB;
};

/** The size typed in megabytes as bytes for saving; empty stays empty (the default applies). */
export const megabytesToBytes = (megabytes: string): string => {
  const text = megabytes.trim();
  return text === "" ? "" : String(Number(text) * MB);
};
