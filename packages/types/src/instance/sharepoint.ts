/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TInstanceSharePointConfigurationKeys =
  | "IS_SHAREPOINT_ENABLED"
  | "SHAREPOINT_TENANT_ID"
  | "SHAREPOINT_CLIENT_ID"
  | "SHAREPOINT_CLIENT_SECRET"
  | "SHAREPOINT_MAX_FILE_SIZE";

export type TSharePointSite = {
  id: string;
  name: string;
  web_url: string;
};

/** A document library (a Graph "drive") of a site. */
export type TSharePointLibrary = {
  id: string;
  name: string;
  web_url: string;
};

/** What "Test connection" answers when it worked. `site` is null when no site URL was given: only the sign-in ran. */
export type TSharePointConnectionTest = {
  site: TSharePointSite | null;
  libraries: TSharePointLibrary[];
};

/** What "Test connection" answers when it did not work. */
export type TSharePointConnectionTestError = {
  /** A message for the administrator. */
  error: string;
  /** The case, for example `invalid_credentials`, `tenant_not_found`, `site_access_denied`, `site_not_found`. */
  error_code: string;
  /** What Microsoft said, shortened; may be empty. */
  detail?: string;
};
