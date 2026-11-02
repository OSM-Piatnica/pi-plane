/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** What went wrong when a message to the admins was not sent: the person has written too much, or too often. */
export type TAdminMessageFailure = "rate_limited" | "other";

export const getAdminMessageFailure = (error: unknown): TAdminMessageFailure => {
  const response = error as { status?: number; data?: { code?: string } } | undefined;
  return response?.status === 429 || response?.data?.code === "RATE_LIMITED" ? "rate_limited" : "other";
};

/** The longest message the API takes (MESSAGE_MAX_LENGTH of the API). */
export const ADMIN_MESSAGE_MAX_LENGTH = 2000;
