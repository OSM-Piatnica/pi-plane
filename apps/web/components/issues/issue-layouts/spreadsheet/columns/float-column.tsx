/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { Row } from "@plane/blocks/layout";
import type { TIssue } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { useWorkItemFloat } from "@/hooks/use-work-item-float";

type Props = {
  issue: TIssue;
};

/** Working days the work item can slip without moving the end of the project; red on the critical path. */
export const SpreadsheetFloatColumn = observer(function SpreadsheetFloatColumn(props: Props) {
  const { issue } = props;
  const float = useWorkItemFloat(issue);

  return (
    <Row
      className={cn(
        "flex h-11 w-full items-center border-b-[0.5px] border-subtle text-11 group-[.selected-issue-row]:bg-accent-primary/5 hover:bg-layer-1 group-[.selected-issue-row]:hover:bg-accent-primary/10",
        { "text-danger-primary": float?.isCritical }
      )}
      title={float?.help}
      data-testid="spreadsheet-float"
    >
      {float?.label}
    </Row>
  );
});
