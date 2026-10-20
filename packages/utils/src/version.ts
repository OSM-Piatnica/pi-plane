/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Splits "v1.3.1-pi.2" or "1.3.1+pi.2" into ["1", "3", "1", "pi", "2"].
const versionParts = (version: string): string[] =>
  version
    .trim()
    .replace(/^v/i, "")
    .split(/[.\-+]/)
    .filter((part) => part !== "");

/**
 * Whether `latest` is a newer release than `current`.
 *
 * Both are release strings such as "1.3.1-pi.2" (a leading "v" is ignored, and "+" and "-" are treated alike).
 * Parts are compared left to right, numerically when both are numbers, otherwise as text. When one version is a
 * prefix of the other, the longer one is newer ("1.3.1-pi.2" is newer than "1.3.1"), which matches how this
 * fork numbers its releases. Empty or missing values are never newer.
 */
export const isNewerVersion = (latest: string | null | undefined, current: string | null | undefined): boolean => {
  if (!latest || !current) return false;
  const a = versionParts(latest);
  const b = versionParts(current);
  if (a.length === 0 || b.length === 0) return false;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const left = a[i];
    const right = b[i];
    if (left === undefined) return false;
    if (right === undefined) return true;
    if (left === right) continue;
    const bothNumeric = /^\d+$/.test(left) && /^\d+$/.test(right);
    return bothNumeric ? Number(left) > Number(right) : left > right;
  }
  return false;
};
