/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserPermissions } from "@plane/constants";
import type { IWorkspaceMember } from "@plane/types";

export type TContactableAdmin = {
  id: string;
  name: string;
  /** Not given to every role: a guest's member list carries no email addresses. */
  email: string | null;
};

/**
 * The admins of a workspace a person can turn to: the active ones, other than the person themselves.
 * Bots are not people to write to.
 */
export const getContactableAdmins = (
  members: ReadonlyArray<IWorkspaceMember | null | undefined>,
  currentUserId?: string | null
): TContactableAdmin[] => {
  const admins = new Map<string, TContactableAdmin>();
  for (const entry of members) {
    const user = entry?.member;
    if (!entry || !user || entry.role !== EUserPermissions.ADMIN || entry.is_active === false) continue;
    if (user.is_bot || user.id === currentUserId) continue;
    admins.set(user.id, { id: user.id, name: user.display_name || user.email || "", email: user.email || null });
  }
  return [...admins.values()];
};

/** A `mailto:` link to all of the given addresses, or null when there is nobody to write to. */
export const buildMailtoHref = (emails: ReadonlyArray<string>, subject: string, body: string): string | null => {
  const addresses = [...new Set(emails.map((email) => email.trim()).filter(Boolean))];
  if (addresses.length === 0) return null;
  // The "@" stays as it is: it is allowed in a mailto address and some mail apps do not decode it
  const to = addresses.map((address) => encodeURIComponent(address).replace(/%40/g, "@")).join(",");
  return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
};
