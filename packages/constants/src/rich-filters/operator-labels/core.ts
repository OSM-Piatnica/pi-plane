/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TCoreSupportedOperators, TCoreSupportedDateFilterOperators } from "@plane/types";
import { CORE_EQUALITY_OPERATOR, CORE_COLLECTION_OPERATOR, CORE_COMPARISON_OPERATOR } from "@plane/types";
import { OPERATOR_LABEL_KEY_PREFIX } from "./prefix";

/**
 * Core operator labels, as translation keys (see OPERATOR_LABEL_KEY_PREFIX): translate them where they are shown.
 */
export const CORE_OPERATOR_LABELS_MAP: Record<TCoreSupportedOperators, string> = {
  [CORE_EQUALITY_OPERATOR.EXACT]: `${OPERATOR_LABEL_KEY_PREFIX}exact`,
  [CORE_COLLECTION_OPERATOR.IN]: `${OPERATOR_LABEL_KEY_PREFIX}in`,
  [CORE_COMPARISON_OPERATOR.RANGE]: `${OPERATOR_LABEL_KEY_PREFIX}range`,
} as const;

/**
 * Core date-specific operator labels
 */
export const CORE_DATE_OPERATOR_LABELS_MAP: Record<TCoreSupportedDateFilterOperators, string> = {
  [CORE_EQUALITY_OPERATOR.EXACT]: `${OPERATOR_LABEL_KEY_PREFIX}exact`,
  [CORE_COMPARISON_OPERATOR.RANGE]: `${OPERATOR_LABEL_KEY_PREFIX}range`,
} as const;
