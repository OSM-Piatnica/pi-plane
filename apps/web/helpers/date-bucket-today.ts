/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TBucketToday } from "@plane/utils";
import { getTodayInTimeZone } from "@plane/utils";

/**
 * The day the time buckets of a date are counted from: today in the person's profile time zone, which is what the
 * API uses to bucket (the browser's own zone only when no zone is known).
 */
export const getBucketToday = (timeZone?: string | null): TBucketToday =>
  timeZone ? getTodayInTimeZone(timeZone) : new Date();
