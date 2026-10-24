/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { OPERATOR_LABEL_KEY_PREFIX } from "@plane/constants";

/** The label of a filter operator in the user's language: operator labels are translation keys, other text stays. */
export const translateOperatorLabel = (t: (key: string) => string, label: string): string =>
  label.startsWith(OPERATOR_LABEL_KEY_PREFIX) ? t(label) : label;
