/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TIssueActivity } from "@plane/types";

export const getRelationActivityContent = (activity: TIssueActivity | undefined): string | undefined => {
  if (!activity) return;

  switch (activity.field) {
    case "blocking":
      return activity.old_value === ""
        ? `marked this work item is blocking work item `
        : `removed the blocking work item `;
    case "blocked_by":
      return activity.old_value === ""
        ? `marked this work item is being blocked by `
        : `removed this work item being blocked by work item `;
    case "duplicate":
      return activity.old_value === ""
        ? `marked this work item as duplicate of `
        : `removed this work item as a duplicate of `;
    case "relates_to":
      return activity.old_value === "" ? `marked that this work item relates to ` : `removed the relation from `;
    case "start_before":
      return activity.old_value === ""
        ? `marked this work item starts before `
        : `removed the starts before relation to `;
    case "start_after":
      return activity.old_value === ""
        ? `marked this work item starts after `
        : `removed the starts after relation to `;
    case "finish_before":
      return activity.old_value === ""
        ? `marked this work item finishes before `
        : `removed the finishes before relation to `;
    case "finish_after":
      return activity.old_value === ""
        ? `marked this work item finishes after `
        : `removed the finishes after relation to `;
  }

  return;
};
