/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane types
import type { TIssueServiceType, TWorkItemWidgets } from "@plane/types";

export type TWorkItemAdditionalWidgetCollapsiblesProps = {
  disabled: boolean;
  hideWidgets: TWorkItemWidgets[];
  issueServiceType: TIssueServiceType;
  projectId: string;
  workItemId: string;
  workspaceSlug: string;
};

export function WorkItemAdditionalWidgetCollapsibles(_props: TWorkItemAdditionalWidgetCollapsiblesProps) {
  return null;
}
