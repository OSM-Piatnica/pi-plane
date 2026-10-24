/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { OIDC_PROVIDER_DEFINITIONS, OIDC_PROVIDER_KEYS } from "@plane/constants";

// The server derives the names of the instance settings from the key of the provider
// (apps/api/plane/authentication/provider/oidc/spec.py: prefix = key.upper().replace("-", "_"))
describe("single sign-on provider definitions", () => {
  it.each(OIDC_PROVIDER_KEYS)("%s is stored under the settings the server reads", (key) => {
    const provider = OIDC_PROVIDER_DEFINITIONS[key];
    expect(provider.key).toBe(key);
    expect(provider.prefix).toBe(key.toUpperCase().replaceAll("-", "_"));
  });

  it.each(OIDC_PROVIDER_KEYS)("%s has no duplicate or reserved settings", (key) => {
    const names = OIDC_PROVIDER_DEFINITIONS[key].fields.map((field) => field.name);
    expect(new Set(names).size).toBe(names.length);
    const common = new Set(["CLIENT_ID", "CLIENT_SECRET", "ENABLE_SIGNUP", "ALLOWED_EMAIL_DOMAINS"]);
    expect(names.filter((name) => common.has(name))).toEqual([]);
  });

  it("lists Microsoft Entra first, then Google and the generic provider", () => {
    expect(OIDC_PROVIDER_KEYS).toEqual(["entra", "google-oidc", "oidc"]);
  });
});
