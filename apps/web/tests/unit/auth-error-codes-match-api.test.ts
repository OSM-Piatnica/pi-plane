/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { EAuthenticationErrorCodes } from "../../helpers/authentication.helper";

vi.mock("next/link", () => ({ default: () => null }));

// A code the web app does not know renders no message at all: the person is bounced to the sign-in page with a number
// in the URL. So every code of the API has to be known here, by number.
const apiSource = readFileSync(
  resolve(import.meta.dirname, "../../../../apps/api/plane/authentication/adapter/error.py"),
  "utf8"
).split("class AuthenticationException")[0];
const apiCodes = Object.fromEntries([...apiSource.matchAll(/"([A-Z_]+)": (\d+)/g)].map((m) => [m[1], m[2]]));
const webCodes = new Set<string>(Object.values(EAuthenticationErrorCodes));

// Codes of the API that the web app never mapped (before single sign-on). Remove an entry when its message is added;
// never add one for a new code.
const KNOWN_UNMAPPED = [
  "EMAIL_PASSWORD_AUTHENTICATION_DISABLED",
  "GITEA_NOT_CONFIGURED",
  "GITHUB_USER_NOT_IN_ORG",
  "GITEA_OAUTH_PROVIDER_ERROR",
  "AUTHENTICATION_FAILED",
];

describe("authentication error codes of the API", () => {
  it("reads the API codes", () => {
    expect(Object.keys(apiCodes).length).toBeGreaterThan(50);
  });

  it("are all known to the web app, except the ones listed as unmapped", () => {
    const unknown = Object.entries(apiCodes)
      .filter(([name, code]) => !webCodes.has(code) && !KNOWN_UNMAPPED.includes(name))
      .map(([name]) => name);
    expect(unknown).toEqual([]);
  });

  it("do not list codes that the web app knows by now", () => {
    expect(KNOWN_UNMAPPED.filter((name) => webCodes.has(apiCodes[name]))).toEqual([]);
  });
});
