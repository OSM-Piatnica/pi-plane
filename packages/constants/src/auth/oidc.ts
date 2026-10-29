/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TOidcProviderKey, TOidcProviderOption } from "@plane/types";

export type TOidcSettingField = {
  /** The setting without the provider prefix: `TENANT_ID` is stored as `ENTRA_TENANT_ID`. */
  name: string;
  label: string;
  type: "text" | "password";
  required?: boolean;
  placeholder?: string;
  description: string;
};

/**
 * What the god-mode form of a single sign-on provider shows. Mirrors the specs of the server
 * (apps/api/plane/authentication/provider/oidc/providers.py): a new provider is one entry here.
 */
export type TOidcProviderDefinition = {
  key: TOidcProviderKey;
  /** Prefix of the instance settings, e.g. `ENTRA` for `IS_ENTRA_ENABLED` and `ENTRA_CLIENT_ID`. */
  prefix: string;
  name: string;
  description: string;
  icon: TOidcProviderOption["icon"];
  /** Where the client id and secret are created. */
  consoleUrl: string;
  consoleName: string;
  /** The settings between the client secret and the common ones. */
  fields: TOidcSettingField[];
};

export const OIDC_PROVIDER_DEFINITIONS: Record<TOidcProviderKey, TOidcProviderDefinition> = {
  entra: {
    key: "entra",
    prefix: "ENTRA",
    name: "Microsoft Entra ID",
    description:
      "Allow members of your Microsoft Entra tenant to log in or sign up for Pi-Plane with their work accounts.",
    icon: "microsoft",
    consoleUrl: "https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
    consoleName: "Microsoft Entra app registration",
    fields: [
      {
        name: "TENANT_ID",
        label: "Directory (tenant) ID",
        type: "text",
        required: true,
        placeholder: "11111111-2222-3333-4444-555555555555",
        description:
          'The GUID of your tenant, from the app registration overview. Only people of this tenant can sign in; domain names and "common" are not accepted.',
      },
    ],
  },
  "google-oidc": {
    key: "google-oidc",
    prefix: "GOOGLE_OIDC",
    name: "Google (OpenID Connect)",
    description:
      "Allow members to log in or sign up for Pi-Plane with their Google accounts, optionally limited to one Google Workspace.",
    icon: "google",
    consoleUrl: "https://console.cloud.google.com/apis/credentials",
    consoleName: "Google Cloud OAuth client",
    fields: [
      {
        name: "HOSTED_DOMAIN",
        label: "Google Workspace domain",
        type: "text",
        placeholder: "example.com",
        description: "Optional. Only accounts of this Google Workspace domain can sign in.",
      },
    ],
  },
  oidc: {
    key: "oidc",
    prefix: "OIDC",
    name: "OpenID Connect",
    description:
      "Allow members to log in or sign up for Pi-Plane with any OpenID Connect provider (Keycloak, Okta, Authentik, ...).",
    icon: "key",
    consoleUrl: "",
    consoleName: "your identity provider",
    fields: [
      {
        name: "ISSUER_URL",
        label: "Issuer URL",
        type: "text",
        required: true,
        placeholder: "https://sso.example.com/realms/main",
        description:
          "The https issuer of the provider. Its /.well-known/openid-configuration is read from here. The provider must verify email addresses.",
      },
      {
        name: "DISPLAY_NAME",
        label: "Button label",
        type: "text",
        placeholder: "Single sign-on",
        description: "How the sign-in button is named.",
      },
    ],
  },
};

export const OIDC_PROVIDER_KEYS = Object.keys(OIDC_PROVIDER_DEFINITIONS) as TOidcProviderKey[];
