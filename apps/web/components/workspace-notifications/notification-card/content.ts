/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TNotificationContentMap } from "@/components/workspace-notifications/sidebar/notification-card/content";

// Additional notification content map for CE (empty - EE extends this)
export const ADDITIONAL_NOTIFICATION_CONTENT_MAP: TNotificationContentMap = {};

// The phrase for a field that has no handler in the map, by field and verb; the same phrase serves the verbs
// that are not listed for a field.
const FALLBACK_ACTION_KEYS: Record<string, Partial<Record<"created" | "updated" | "deleted", string>>> = {
  state: { updated: "notification.content.state_updated" },
  priority: { updated: "notification.content.priority_updated" },
  name: { updated: "notification.content.name_updated" },
  type: { updated: "notification.content.type_updated" },
  estimate_point: { updated: "notification.content.estimate_updated" },
  cycles: {
    created: "notification.content.cycle_added",
    updated: "notification.content.cycle_updated",
    deleted: "notification.content.cycle_removed",
  },
  modules: {
    created: "notification.content.module_added",
    updated: "notification.content.module_updated",
    deleted: "notification.content.module_removed",
  },
  link: {
    created: "notification.content.link_added",
    updated: "notification.content.link_updated",
    deleted: "notification.content.link_removed",
  },
  attachment: {
    created: "notification.content.attachment_added",
    deleted: "notification.content.attachment_removed",
  },
  blocking: {
    created: "notification.content.blocking_added",
    deleted: "notification.content.blocking_removed",
  },
  blocked_by: {
    created: "notification.content.blocked_by_added",
    deleted: "notification.content.blocked_by_removed",
  },
};

// Fallback action renderer for fields not in the map
export const renderAdditionalAction = (
  notificationField: string,
  verb: string | undefined,
  t: (key: string) => string
): string => {
  const actions = FALLBACK_ACTION_KEYS[notificationField];
  const key = actions?.[verb as "created" | "updated" | "deleted"] ?? actions?.updated ?? actions?.created ?? undefined;
  return t(key ?? "notification.content.generic_updated");
};

// Fallback value renderer for fields not in the map
export const renderAdditionalValue = (
  _notificationField: string | undefined,
  newValue: string | undefined,
  _oldValue: string | undefined
) => newValue;

export const shouldRender = (notificationField: string | undefined, verb: string | undefined) => verb !== "deleted";
