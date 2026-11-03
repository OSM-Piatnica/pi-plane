/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TNotificationGroupMembership } from "@plane/types";

/** The inbox text about the person's place in a group: added as a member or as an admin, promoted, or demoted. */
export const getGroupMembershipNotificationTextKey = (membership: TNotificationGroupMembership | undefined) => {
  if (membership?.event === "added") {
    return membership.role === "admin"
      ? "notification.group_membership.added_admin"
      : "notification.group_membership.added";
  }
  return membership?.role === "admin"
    ? "notification.group_membership.promoted"
    : "notification.group_membership.demoted";
};

/** Where a click on that inbox entry leads: the groups of the workspace. */
export const getGroupMembershipNotificationPath = (workspaceSlug: string) => `/${workspaceSlug}/settings/groups/`;
