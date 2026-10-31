/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { clone, concat, pull, uniq } from "lodash-es";
// plane imports
import type { TBucketToday } from "@plane/utils";
import { getDateBucketDropDate, getDateBucketEdge, isDateBucketGroupBy } from "@plane/utils";
import type { TIssueGroupByOptions } from "@plane/types";

/**
 * The new value of the property a group by is made of, after a work item was dropped from one group into another.
 * - a list property (labels, assignees...): the source group leaves it and the destination group joins it
 * - a time bucket of a date: the day that stands for the destination bucket, a working day by `weekendDays`
 *   (the last one of a week for a finish or due date, the first one for a start date)
 * - anything else: the destination group, or nothing for the "None" group
 *
 * Returns `undefined` when the drop cannot be made: a time bucket that names no single day (Earlier, Later, or
 * This week once no working day is left in it).
 */
export const getGroupDropValue = (
  groupBy: TIssueGroupByOptions,
  currentValue: unknown,
  sourceGroupId: string,
  destinationGroupId: string,
  today?: TBucketToday,
  weekendDays?: readonly number[]
): unknown => {
  if (Array.isArray(currentValue)) {
    const value: string[] = clone(currentValue);
    pull(value, sourceGroupId);
    return destinationGroupId === "None" ? value : uniq(concat(value, [destinationGroupId]));
  }
  if (isDateBucketGroupBy(groupBy)) {
    return getDateBucketDropDate(destinationGroupId, today, { weekendDays, edge: getDateBucketEdge(groupBy) });
  }
  return destinationGroupId === "None" ? null : destinationGroupId;
};
