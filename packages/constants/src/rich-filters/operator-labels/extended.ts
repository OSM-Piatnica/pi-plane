/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type {
  TExtendedSupportedOperators,
  TNegatedOperator,
  TSupportedDateFilterOperators,
  TSupportedOperators,
} from "@plane/types";
import { OPERATOR_LABEL_KEY_PREFIX } from "./prefix";

/**
 * Extended operator labels
 */
export const EXTENDED_OPERATOR_LABELS_MAP: Record<TExtendedSupportedOperators, string> = {} as const;

/**
 * Extended date-specific operator labels
 */
export const EXTENDED_DATE_OPERATOR_LABELS_MAP: Record<TExtendedSupportedOperators, string> = {} as const;

/**
 * Negated operator labels for all operators
 */
export const NEGATED_OPERATOR_LABELS_MAP: Record<TNegatedOperator<TSupportedOperators>, string> = {
  not_exact: `${OPERATOR_LABEL_KEY_PREFIX}not_exact`,
  not_in: `${OPERATOR_LABEL_KEY_PREFIX}not_in`,
  not_range: `${OPERATOR_LABEL_KEY_PREFIX}not_range`,
} as const;

/**
 * Negated date operator labels for all date operators
 */
export const NEGATED_DATE_OPERATOR_LABELS_MAP: Record<TNegatedOperator<TSupportedDateFilterOperators>, string> = {
  not_exact: `${OPERATOR_LABEL_KEY_PREFIX}not_exact`,
  not_range: `${OPERATOR_LABEL_KEY_PREFIX}not_range`,
} as const;
