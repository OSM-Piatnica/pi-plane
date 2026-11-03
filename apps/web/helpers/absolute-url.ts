/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * The URL with its host: a relative path (`/api/assets/...`, what the app has when it runs on the same address as
 * its API) is taken to be on `origin`, which is the page's own. The API's `cover_image` field only takes a full URL.
 */
export const toAbsoluteURL = (url: string, origin: string = globalThis.location?.origin ?? ""): string => {
  if (/^https?:\/\//i.test(url) || !origin) return url;
  return new URL(url, origin).toString();
};
