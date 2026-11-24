/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isRouteErrorResponse } from "react-router";

/** What kind of failure the error page is shown for, so that it can say something more useful than "went wrong". */
export type TErrorKind = "offline" | "access" | "not_found" | "server" | "generic";

// What browsers and axios say when a request never got an answer
const NETWORK_FAILURE_MESSAGES = [
  "Network Error", // axios
  "Failed to fetch", // Chromium
  "NetworkError when attempting to fetch", // Firefox
  "Load failed", // Safari
];

const getMessage = (error: unknown): string =>
  error instanceof Error ? error.message : typeof error === "string" ? error : "";

/** The HTTP status an error carries: a route error response, an axios error or anything with a `status`. */
export const getErrorStatus = (error: unknown): number | undefined => {
  if (isRouteErrorResponse(error)) return error.status;
  if (typeof error !== "object" || error === null) return undefined;
  const { response, status } = error as { response?: { status?: unknown }; status?: unknown };
  if (typeof response?.status === "number") return response.status;
  return typeof status === "number" ? status : undefined;
};

export const getErrorKind = (error: unknown, isOnline: boolean = defaultIsOnline()): TErrorKind => {
  const status = getErrorStatus(error);
  if (status === 401 || status === 403) return "access";
  if (status === 404) return "not_found";
  if (status !== undefined && status >= 500) return "server";
  if (!isOnline) return "offline";
  // Online, but a request got no answer at all: the server could not be reached
  if (status === undefined && NETWORK_FAILURE_MESSAGES.some((text) => getMessage(error).includes(text)))
    return "server";
  return "generic";
};

// Only an explicit `false` means offline: other environments (and old browsers) do not report it at all
const defaultIsOnline = (): boolean => typeof navigator === "undefined" || navigator.onLine !== false;
