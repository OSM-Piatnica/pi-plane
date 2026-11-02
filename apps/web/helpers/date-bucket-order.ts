/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { DEFAULT_WORK_ITEM_ORDER_BY } from "@plane/constants";
import type { IIssueDisplayFilterOptions, TIssueOrderByOptions } from "@plane/types";
import { DATE_BUCKET_GROUP_BY_FIELDS, isDateBucketGroupBy } from "@plane/utils";

/**
 * The order to switch to when a list is grouped by the bucket of a date: that date, earliest first (work items
 * without it last), so the dates run in sequence inside every bucket. Nothing (keep the order) when
 * - the update does not group by a date bucket, or
 * - the same update picks an order itself, or
 * - the list is not in the default order, i.e. the person chose an order of their own.
 *
 * @param updated - The display filters being changed
 * @param merged - The display filters as they are once the update is applied
 */
export const getDateBucketOrderBy = (
  updated: IIssueDisplayFilterOptions,
  merged: IIssueDisplayFilterOptions
): TIssueOrderByOptions | undefined => {
  if (!isDateBucketGroupBy(updated.group_by)) return undefined;
  if ("order_by" in updated) return undefined;
  if (merged.order_by && merged.order_by !== DEFAULT_WORK_ITEM_ORDER_BY) return undefined;
  return DATE_BUCKET_GROUP_BY_FIELDS[updated.group_by];
};
