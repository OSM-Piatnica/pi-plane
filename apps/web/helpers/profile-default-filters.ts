/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TWorkItemFilterExpression } from "@plane/types";

/**
 * What "Your work" shows before the person has chosen anything: the work that is still to do or in progress
 * (the "To do" and "In progress" state groups). Backlog, done and cancelled work is one filter away.
 */
export const DEFAULT_PROFILE_RICH_FILTERS: TWorkItemFilterExpression = { state_group__in: "unstarted,started" };

/**
 * The filters of the "Your work" screen: the person's own when they have any, including an empty set they
 * cleared on purpose, else the default. A stored filter is `undefined` only when nothing was ever chosen.
 */
export const resolveProfileRichFilters = (stored: TWorkItemFilterExpression | null | undefined) =>
  stored ?? DEFAULT_PROFILE_RICH_FILTERS;
