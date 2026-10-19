/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { CORE_GANTT_TIMELINE_TYPE } from "./core";
import { EXTENDED_GANTT_TIMELINE_TYPE } from "./extended";

export const GANTT_TIMELINE_TYPE = {
  ...CORE_GANTT_TIMELINE_TYPE,
  ...EXTENDED_GANTT_TIMELINE_TYPE,
} as const;

export type TTimelineTypeCore = (typeof CORE_GANTT_TIMELINE_TYPE)[keyof typeof CORE_GANTT_TIMELINE_TYPE];
export type TTimelineType =
  | TTimelineTypeCore
  | (typeof EXTENDED_GANTT_TIMELINE_TYPE)[keyof typeof EXTENDED_GANTT_TIMELINE_TYPE];
