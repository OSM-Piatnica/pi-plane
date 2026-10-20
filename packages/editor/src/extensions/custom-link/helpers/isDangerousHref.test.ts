/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { isDangerousHref } from "./isDangerousHref";

describe("isDangerousHref", () => {
  it.each([
    "javascript:alert(1)",
    "JAVASCRIPT:alert(1)",
    "  javascript:alert(1)",
    "\tjavascript:alert(1)",
    "\n\rjavascript:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    "jav\r\nascript:alert(1)",
    "\u0001javascript:alert(1)",
    "\u001fjavascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    " DaTa:text/html;base64,AAAA",
    "vbscript:msgbox(1)",
    "\tVBScript:msgbox(1)",
  ])("blocks %j", (href) => {
    expect(isDangerousHref(href)).toBe(true);
  });

  it.each([
    "",
    "https://example.com",
    "http://example.com/?q=javascript:alert(1)",
    "mailto:user@example.com",
    "/relative/path",
    "#anchor",
    "example.com/javascript:foo",
    "javascript",
  ])("allows %j", (href) => {
    expect(isDangerousHref(href)).toBe(false);
  });
});
