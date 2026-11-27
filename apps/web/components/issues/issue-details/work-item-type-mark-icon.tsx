/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Logo } from "@plane/blocks/emoji-icon-picker";
import {
  ApproverOutline,
  CheckSquareOutline,
  EpicOutline,
  MilestoneOutline,
  WorkItemsOutline,
} from "@makeplane/propel/icons";
import type { TIssueType, TLogoProps } from "@plane/types";
import { getWorkItemTypeMarkKind } from "@/helpers/work-item-type-mark";

/** The mark of a work item type: the logo an admin picked, else a built-in one for its kind, else a general one. */
export function WorkItemTypeMarkIcon(props: { issueType: TIssueType; size?: number }) {
  const { issueType, size = 16 } = props;
  const iconProps = { width: size, height: size };
  switch (getWorkItemTypeMarkKind(issueType)) {
    case "logo":
      return <Logo logo={issueType.logo_props as TLogoProps} size={size} />;
    case "epic":
      return <EpicOutline {...iconProps} className="text-accent-primary" />;
    case "milestone":
      return <MilestoneOutline {...iconProps} className="text-accent-primary" />;
    case "approval":
      return <ApproverOutline {...iconProps} className="text-accent-primary" />;
    case "review":
      return <CheckSquareOutline {...iconProps} className="text-accent-primary" />;
    default:
      return <WorkItemsOutline {...iconProps} className="text-tertiary" />;
  }
}
