/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// The largest file for SharePoint (instance setting SHAREPOINT_MAX_FILE_SIZE). The API stores bytes and reads them
// in `plane/utils/sharepoint/config.py`; these helpers mirror that reading so the admin app shows what applies.

const MB = 1024 * 1024;

/** What applies while no usable size is saved: 500 MB. */
export const SHAREPOINT_DEFAULT_MAX_FILE_SIZE = 500 * MB;
/** The smallest size that can be saved: 1 MB. */
export const SHAREPOINT_MIN_MAX_FILE_SIZE = MB;
/** The largest size that can be saved: what SharePoint Online takes for one file, 250 GB. */
export const SHAREPOINT_MAX_MAX_FILE_SIZE = 250 * 1024 * MB;

export type TSharePointMaxFileSize = {
  /** The size the API applies, in bytes. */
  applied: number;
  /** No usable size is saved, so the default applies. */
  isDefault: boolean;
  /** A saved value that the API cannot use (not a whole number of bytes, or out of range), so it applies the default. */
  ignoredValue: string | undefined;
};

/** The saved value in bytes as the API reads it: a whole number within range, else undefined. */
export const parseSharePointMaxFileSize = (raw: string | null | undefined): number | undefined => {
  const text = (raw ?? "").trim();
  if (!/^\d+$/.test(text)) return undefined;
  const bytes = Number(text);
  return bytes >= SHAREPOINT_MIN_MAX_FILE_SIZE && bytes <= SHAREPOINT_MAX_MAX_FILE_SIZE ? bytes : undefined;
};

/** What the API applies for the saved value, and whether the saved value is being ignored. */
export const getSharePointMaxFileSize = (raw: string | null | undefined): TSharePointMaxFileSize => {
  const saved = parseSharePointMaxFileSize(raw);
  const text = (raw ?? "").trim();
  return {
    applied: saved ?? SHAREPOINT_DEFAULT_MAX_FILE_SIZE,
    isDefault: saved === undefined,
    ignoredValue: saved === undefined && text !== "" ? text : undefined,
  };
};

/**
 * Bytes as megabytes for the input field, never rounded to whole megabytes: 1000000000 shows as 953.67431640625, not
 * 954, so a value set in bytes (for example from the environment) is not changed by showing it. The text converts
 * back (megabytesTextToBytes) to exactly the same bytes.
 */
export const bytesToMegabytesText = (bytes: number): string => String(bytes / MB);

/** Megabytes typed into the field as whole bytes, or undefined when the text is not a positive number. */
export const megabytesTextToBytes = (text: string): number | undefined => {
  const trimmed = text.trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) return undefined;
  const bytes = Math.round(Number(trimmed) * MB);
  return Number.isFinite(bytes) && bytes > 0 ? bytes : undefined;
};

/**
 * What to save for the text of the field: "" (back to the default) when it is empty, the bytes when it is a size
 * that can be saved, undefined when it cannot be saved.
 */
export const sharePointMaxFileSizeToSave = (text: string): string | undefined => {
  if (text.trim() === "") return "";
  const bytes = megabytesTextToBytes(text);
  if (bytes === undefined || bytes < SHAREPOINT_MIN_MAX_FILE_SIZE || bytes > SHAREPOINT_MAX_MAX_FILE_SIZE) {
    return undefined;
  }
  return String(bytes);
};
