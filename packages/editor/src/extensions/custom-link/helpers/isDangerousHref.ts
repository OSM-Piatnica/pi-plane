/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Blocked link protocols — browsers execute these in the page's security context.
const BLOCKED_LINK_PROTOCOLS = ["javascript:", "data:", "vbscript:"];

/**
 * Returns true if the raw href value contains a dangerous protocol.
 *
 * Per the WHATWG URL spec, browsers strip ASCII Tab (U+0009), LF (U+000A), and
 * CR (U+000D) from URL strings during parsing, and strip leading C0 controls /
 * whitespace before the scheme. A naive `startsWith("javascript:")` check is
 * therefore bypassable with a whitespace prefix (e.g. `"\tjavascript:alert(1)"`).
 * We replicate that normalization before our protocol check (GHSA-v2vv-7wq3-8w2j).
 */
export function isDangerousHref(rawHref: string): boolean {
  const normalized = rawHref
    .replace(/[\t\n\r]/g, "") // strip Tab/LF/CR (stripped anywhere by WHATWG parser)
    // oxlint-disable-next-line no-control-regex -- intentional: mirrors WHATWG C0-control stripping before the URL scheme
    .replace(/^[\s\u0000-\u0008\u000E-\u001F]+/, "") // strip leading C0 controls + whitespace
    .toLowerCase();
  return BLOCKED_LINK_PROTOCOLS.some((protocol) => normalized.startsWith(protocol));
}
