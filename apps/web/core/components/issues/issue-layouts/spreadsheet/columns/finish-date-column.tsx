/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { DueDatePropertyIcon } from "@plane/propel/icons";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
// types
import type { TIssue } from "@plane/types";
import { cn, getDate, renderFormattedPayloadDate, validateWorkItemSchedule } from "@plane/utils";
// components
import { DateDropdown } from "@/components/dropdowns/date";
// helpers
// hooks

type Props = {
  issue: TIssue;
  onClose: () => void;
  onChange: (issue: TIssue, data: Partial<TIssue>, updates: any) => void;
  disabled: boolean;
};

export const SpreadsheetFinishDateColumn = observer(function SpreadsheetFinishDateColumn(props: Props) {
  const { issue, onChange, disabled, onClose } = props;
  const { t } = useTranslation();

  return (
    <div className="h-11 border-b-[0.5px] border-subtle">
      <DateDropdown
        value={issue.finish_date}
        minDate={getDate(issue.start_date)}
        onChange={(data) => {
          const finishDate = data ? renderFormattedPayloadDate(data) : null;
          // finish may not precede start; reject without changing any other field
          if (validateWorkItemSchedule(issue.start_date, finishDate)) {
            setToast({
              type: TOAST_TYPE.ERROR,
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
        icon={<DueDatePropertyIcon className="h-3 w-3 flex-shrink-0" />}
        buttonVariant="transparent-with-text"
        buttonContainerClassName="w-full"
        buttonClassName={cn(
          "rounded-none px-page-x text-left group-[.selected-issue-row]:bg-accent-primary/5 group-[.selected-issue-row]:hover:bg-accent-primary/10"
        )}
        optionsClassName="z-[9]"
        clearIconClassName="!text-primary"
        onClose={onClose}
      />
    </div>
  );
});
