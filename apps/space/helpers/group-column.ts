/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { getStateName } from "@plane/utils";

/**
 * The title of a group-by column. The columns of the group-by-state layouts carry the state id in their
 * payload, so the default state names are translated there; every other column keeps its name.
 */
export const getGroupColumnTitle = (
  column: { name?: string | null; payload?: { state_id?: string | null } },
  t: (key: string) => string
): string => (column.payload?.state_id ? getStateName(column.name ?? "", t) : (column.name ?? ""));
