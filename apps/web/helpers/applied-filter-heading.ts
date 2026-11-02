/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { replaceUnderscoreIfSnakeCase } from "@plane/utils";

// The filter bars of the cycle, module, project, view and page lists are keyed by the filter property names.
// These are the translation keys for the headings of those properties.
const FILTER_HEADING_KEYS = new Map<string, string>(
  Object.entries({
    status: "module_ui.status",
    start_date: "start_date",
    end_date: "end_date",
    target_date: "target_date",
    lead: "lead",
    members: "members",
    groups: "group_filter.heading",
    labels: "labels",
    favorites: "favorites",
    created_at: "common.created_at",
    created_by: "common.created_by",
    access: "filter_headings.access",
    view_type: "filter_headings.access",
    owned_by: "filter_headings.owned_by",
  })
);

/** The heading of an applied filter: translated for the known filter properties, the property name otherwise. */
export const getAppliedFilterHeading = (filterKey: string, t: (key: string) => string): string => {
  const key = FILTER_HEADING_KEYS.get(filterKey);
  return key ? t(key) : replaceUnderscoreIfSnakeCase(filterKey);
};
