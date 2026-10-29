/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { EAuthenticationErrorCodes, authErrorHandler } from "../../helpers/authentication.helper";

// The app resolves `next/link` through its router compat layer; the helper only needs it as a component.
vi.mock("next/link", () => ({ default: () => null }));

const english = JSON.parse(
  readFileSync(resolve(import.meta.dirname, "../../../../packages/i18n/src/locales/en/auth.json"), "utf8")
) as Record<string, unknown>;

const hasKey = (key: string) => {
  let node: unknown = english;
  for (const part of key.split(".")) {
    if (typeof node !== "object" || node === null || !(part in node)) return false;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string";
};

/** A stand-in for `t` that records every key it is asked for. */
const makeT = () => {
  const keys: string[] = [];
  const t = (key: string, params?: Record<string, unknown>) => {
    keys.push(key);
    return params ? `${key}:${JSON.stringify(params)}` : key;
  };
  return { t, keys };
};

const ALL_CODES = Object.values(EAuthenticationErrorCodes);

describe("authErrorHandler", () => {
  it("translates every error code through keys that exist in the English locale", () => {
    const { t, keys } = makeT();
    for (const code of ALL_CODES) {
      const info = authErrorHandler(code, t);
      expect(info, `code ${code}`).toBeDefined();
      expect(info?.title, `code ${code}`).toBeTypeOf("string");
    }
    const missing = [...new Set(keys)].filter((key) => key.startsWith("auth.") && !hasKey(key));
    expect(missing).toEqual([]);
  });

  it("builds the title from a key, and fills a template with the translated title", () => {
    const { t } = makeT();
    const info = authErrorHandler(EAuthenticationErrorCodes.INVALID_EMAIL, t);
    expect(info?.title).toBe("auth.error_alerts.titles.invalid_email");
    expect(info?.message).toBe('auth.error_alerts.try_again:{"title":"auth.error_alerts.titles.invalid_email"}');
  });

  it("keeps the rate limit alert title-less", () => {
    const { t } = makeT();
    const info = authErrorHandler(EAuthenticationErrorCodes.RATE_LIMIT_EXCEEDED, t);
    expect(info?.title).toBe("error");
    expect(info?.message).toBe("auth.error_alerts.rate_limit_exceeded");
  });

  it("returns nothing for a code that is not an auth error", () => {
    const { t } = makeT();
    expect(authErrorHandler("9999" as EAuthenticationErrorCodes, t)).toBeUndefined();
  });
});
