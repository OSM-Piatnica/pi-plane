/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { DueDateOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
// types
import type { TIssue } from "@plane/types";
import { getDate, renderFormattedPayloadDate, validateWorkItemSchedule } from "@plane/utils";
// components
import { DateSelect } from "@/components/dropdowns/date-select";
// hooks
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";

type Props = {
  issue: TIssue;
  onClose: () => void;
  onChange: (issue: TIssue, data: Partial<TIssue>, updates: any) => void;
  disabled: boolean;
};

export const SpreadsheetFinishDateColumn = observer(function SpreadsheetFinishDateColumn(props: Props) {
  const { issue, onChange, disabled, onClose } = props;
  const { t } = useTranslation();
  const startOfTheWeek = useStartOfTheWeek();

  return (
    <div className="h-11 border-b-[0.5px] border-subtle">
      <DateSelect
        value={getDate(issue.finish_date) ?? null}
        minDate={getDate(issue.start_date)}
        onChange={(data) => {
          const finishDate = data ? renderFormattedPayloadDate(data) : null;
          // finish may not precede start; reject without changing any other field
          if (validateWorkItemSchedule(issue.start_date, finishDate)) {
            setToast({
              type: "error",
              title: t("toast.error"),
              message: t("issue.dates.finish_before_start"),
            });
            return;
          }
          onChange(
            issue,
            { finish_date: finishDate },
            {
              changed_property: "finish_date",
              change_details: finishDate,
            }
          );
        }}
        disabled={disabled}
        placeholder={t("common.order_by.finish_date")}
        icon={<DueDateOutline />}
        clearable
        // `.clickable` is what the table's keyboard navigation clicks on Enter / Space in a focused cell.
        className="clickable h-full"
        weekStartsOn={startOfTheWeek}
        onClose={onClose}
        variant="table-cell"
      />
    </div>
  );
});
