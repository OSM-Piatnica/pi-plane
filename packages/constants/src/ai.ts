/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export enum AI_EDITOR_TASKS {
  ASK_ANYTHING = "ASK_ANYTHING",
}

// values are i18n keys, translate where displayed
export const LOADING_TEXTS: {
  [key in AI_EDITOR_TASKS]: string;
} = {
  [AI_EDITOR_TASKS.ASK_ANYTHING]: "app_text.ai.pi_generating_response",
};
