/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TAllAvailableOperatorsForDisplay, TAllAvailableDateFilterOperatorsForDisplay } from "@plane/types";
import { CORE_OPERATOR_LABELS_MAP, CORE_DATE_OPERATOR_LABELS_MAP } from "./core";
import {
  EXTENDED_OPERATOR_LABELS_MAP,
  EXTENDED_DATE_OPERATOR_LABELS_MAP,
  NEGATED_OPERATOR_LABELS_MAP,
  NEGATED_DATE_OPERATOR_LABELS_MAP,
} from "./extended";

/**
 * Empty operator label for unselected state
 */
export const EMPTY_OPERATOR_LABEL = "--";

/**
 * Complete operator labels mapping - combines core, extended, and negated labels
 */
export const OPERATOR_LABELS_MAP: Record<TAllAvailableOperatorsForDisplay, string> = {
  ...CORE_OPERATOR_LABELS_MAP,
  ...EXTENDED_OPERATOR_LABELS_MAP,
  ...NEGATED_OPERATOR_LABELS_MAP,
} as const;

/**
 * Complete date operator labels mapping - combines core, extended, and negated labels
 */
export const DATE_OPERATOR_LABELS_MAP: Record<TAllAvailableDateFilterOperatorsForDisplay, string> = {
  ...CORE_DATE_OPERATOR_LABELS_MAP,
  ...EXTENDED_DATE_OPERATOR_LABELS_MAP,
  ...NEGATED_DATE_OPERATOR_LABELS_MAP,
} as const;

export { OPERATOR_LABEL_KEY_PREFIX } from "./prefix";

// -------- RE-EXPORTS --------

export * from "./core";
export * from "./extended";
