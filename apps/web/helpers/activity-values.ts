/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { capitalizeFirstLetter } from "@plane/utils";

type TTranslate = (key: string, params?: Record<string, unknown>) => string;

/**
 * The priority an activity record stores ("high", "urgent", …) is a key, not text: this is the name of it in the
 * user's language. An empty value means no priority; an unknown one is shown as stored.
 */
export const getPriorityLabel = (priority: string | null | undefined, t: TTranslate): string => {
  switch (priority) {
    case undefined:
    case null:
    case "":
    case "none":
      return t("activity_feed.profile.priority.none");
    case "urgent":
      return t("activity_feed.profile.priority.urgent");
    case "high":
      return t("activity_feed.profile.priority.high");
    case "medium":
      return t("activity_feed.profile.priority.medium");
    case "low":
      return t("activity_feed.profile.priority.low");
    default:
      return capitalizeFirstLetter(priority);
  }
};
