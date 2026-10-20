/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TInboxIssueStatus } from "@plane/types";
import { cn } from "@plane/utils";
import { ICON_PROPERTIES } from "./inbox-status-properties";

export function InboxStatusIcon({
  type,
  size,
  className,
  renderColor = true,
}: {
  type: TInboxIssueStatus;
  size?: number;
  className?: string;
  renderColor?: boolean;
}) {
  if (type === undefined) return null;
  const Icon = ICON_PROPERTIES[type];
  if (!Icon) return null;
  return (
    <Icon.icon
      width={size}
      height={size}
      className={cn(`h-3 w-3 ${renderColor && Icon?.textColor(false)}`, className)}
    />
  );
}
