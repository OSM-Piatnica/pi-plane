/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isRouteErrorResponse } from "react-router";
import type { TErrorKind } from "./error-kind";
import { getErrorStatus } from "./error-kind";

// No 0, O, 1, I or L: a person reads the reference out or types it, so it must not be ambiguous
const REFERENCE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const MAX_MESSAGE_LENGTH = 300;
const UUID_PATTERN = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
const EMAIL_PATTERN = /[^\s@<>()"']+@[^\s@<>()"']+\.[^\s@<>()"']+/g;

/** A short id such as `7K2M-9QXD`, shown on the error page and part of the copied details. */
export const createErrorReference = (
  getRandomBytes: (length: number) => Uint8Array = (length) => crypto.getRandomValues(new Uint8Array(length))
): string => {
  const chars = Array.from(getRandomBytes(8), (byte) => REFERENCE_ALPHABET[byte % REFERENCE_ALPHABET.length]);
  return `${chars.slice(0, 4).join("")}-${chars.slice(4).join("")}`;
};

/** The path of a page without its query string or fragment and without ids that point at a person or a record. */
export const scrubPath = (path: string): string => path.split(/[?#]/)[0].replace(UUID_PATTERN, ":id");

const scrubText = (text: string): string =>
  text.replace(EMAIL_PATTERN, "[email]").replace(UUID_PATTERN, ":id").replace(/\s+/g, " ").trim();

export const describeError = (error: unknown): { name: string; message: string } => {
  if (isRouteErrorResponse(error))
    return { name: "RouteErrorResponse", message: `${error.status} ${error.statusText}` };
  if (error instanceof Error)
    return { name: error.name, message: scrubText(error.message).slice(0, MAX_MESSAGE_LENGTH) };
  const message = typeof error === "string" ? scrubText(error).slice(0, MAX_MESSAGE_LENGTH) : "";
  return { name: error === null ? "null" : typeof error, message };
};

type TErrorDetailsInput = {
  reference: string;
  kind: TErrorKind;
  error: unknown;
  path: string;
  time: Date;
};

/**
 * What a person can copy and send to support: when, where, what. No stack trace, no query string, no
 * emails or record ids, nothing the person typed.
 */
export const buildErrorDetails = ({ reference, kind, error, path, time }: TErrorDetailsInput): string => {
  const { name, message } = describeError(error);
  const status = getErrorStatus(error);
  return [
    `Pi-Plane error ${reference}`,
    `Time: ${time.toISOString()}`,
    `Page: ${scrubPath(path)}`,
    `Kind: ${kind}${status ? ` (HTTP ${status})` : ""}`,
    `Error: ${name}${message ? `: ${message}` : ""}`,
  ].join("\n");
};
