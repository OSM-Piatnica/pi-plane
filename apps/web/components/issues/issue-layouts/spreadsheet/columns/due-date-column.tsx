/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { DueDateOutline } from "@makeplane/propel/icons";
import { DateSelect } from "@/components/dropdowns/date-select";
// types
import type { TIssue } from "@plane/types";
import { cn, getDate, renderFormattedPayloadDate } from "@plane/utils";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { getIssueDateStatuses } from "../../utils";

type Props = {
  issue: TIssue;
  onClose: () => void;
  onChange: (issue: TIssue, data: Partial<TIssue>, updates: any) => void;
  disabled: boolean;
};

export const SpreadsheetDueDateColumn = observer(function SpreadsheetDueDateColumn(props: Props) {
  const { issue, onChange, disabled, onClose } = props;
  // store hooks
  const { getStateById } = useProjectState();
  const startOfTheWeek = useStartOfTheWeek();
  // plane hooks
  const { t } = useTranslation();
  // derived values
  const { getProjectById } = useProject();
  const stateDetails = getStateById(issue.state_id);
  // overdue concerns the due date only and only active work items; the due day itself is not overdue
  const isOverdue = getIssueDateStatuses(
    issue,
    stateDetails?.group,
    getProjectById(issue.project_id)?.timezone
  ).overdue;

  return (
    <div className="h-11 border-b-[0.5px] border-subtle">
      <DateSelect
        value={getDate(issue.target_date) ?? null}
        onChange={(data) => {
          const targetDate = data ? renderFormattedPayloadDate(data) : null;
          onChange(
            issue,
            { target_date: targetDate },
            {
              changed_property: "target_date",
              change_details: targetDate,
            }
          );
        }}
        disabled={disabled}
        placeholder={t("due_date")}
        icon={<DueDateOutline />}
        clearable
        // `.clickable` is what the table's keyboard navigation clicks on Enter / Space in a focused cell.
        className={cn("clickable h-full", {
          "text-danger-primary": isOverdue,
        })}
        weekStartsOn={startOfTheWeek}
        onClose={onClose}
        variant="table-cell"
      />
    </div>
  );
});
