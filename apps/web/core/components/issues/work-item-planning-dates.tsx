/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { AlertTriangle, Timer } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { DueDatePropertyIcon, StartDatePropertyIcon } from "@plane/propel/icons";
import type { TIssue, TStateGroups } from "@plane/types";
import { cn, renderFormattedPayloadDate, shouldHighlightIssueDueDate } from "@plane/utils";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { DateDropdown } from "@/components/dropdowns/date";
import { DurationDropdown } from "@/components/dropdowns/duration";
// hooks
import { useProjectTimeZone, useWorkItemDateEdit, useWorkItemDateStatuses } from "@/hooks/use-work-item-dates";
// plane web imports
import { DateAlert } from "@/plane-web/components/issues/issue-details/sidebar/date-alert";

type Props = {
  issue: TIssue;
  projectId: string;
  stateGroup: TStateGroups | undefined;
  disabled?: boolean;
  /** Existing save operation of the surface (optimistic update, rollback and error toast stay there). */
  onUpdate: (data: Partial<TIssue>) => Promise<void> | void;
  /** Typography differs slightly between the details sidebar and the peek overview. */
  textClassName?: string;
};

/**
 * Start, finish, due and duration of a work item, side by side and independently editable.
 * - Finish is the planned end of the work and drives the duration.
 * - Due is a deadline. It is never moved by, nor does it move, the schedule.
 */
export const WorkItemPlanningDates = observer(function WorkItemPlanningDates(props: Props) {
  const { issue, projectId, stateGroup, disabled, onUpdate, textClassName = "text-body-xs-regular" } = props;
  const { t } = useTranslation();
  const timeZone = useProjectTimeZone(projectId);
  const isActive = stateGroup !== "completed" && stateGroup !== "cancelled";
  const statuses = useWorkItemDateStatuses(issue, isActive, projectId);
  const updateDates = useWorkItemDateEdit(issue, onUpdate);

  const toPayload = (date: Date | null | undefined) => (date ? (renderFormattedPayloadDate(date) ?? null) : null);

  const warnings = [
    statuses.overdue && t("issue.dates.status.overdue"),
    statuses.forecastMissesDeadline && t("issue.dates.status.forecast_misses_deadline"),
    statuses.plannedFinishPassed && t("issue.dates.status.planned_finish_passed"),
    statuses.completedLate && t("issue.dates.status.completed_late"),
  ].filter(Boolean) as string[];

  return (
    <>
      <SidebarPropertyListItem icon={StartDatePropertyIcon} label={t("common.order_by.start_date")}>
        <DateDropdown
          placeholder={t("issue.add.start_date")}
          value={issue.start_date}
          onChange={(val) => void updateDates({ start_date: toPayload(val) })}
          disabled={disabled}
          buttonVariant="transparent-with-text"
          className="group w-full grow"
          buttonContainerClassName="w-full text-left h-7.5"
          buttonClassName={`${textClassName} ${issue?.start_date ? "" : "text-placeholder"}`}
          hideIcon
          clearIconClassName="h-3 w-3 hidden group-hover:inline"
        />
      </SidebarPropertyListItem>

      <SidebarPropertyListItem icon={DueDatePropertyIcon} label={t("common.order_by.finish_date")}>
        <div className="w-full" title={t("issue.dates.help.finish")}>
          <DateDropdown
            placeholder={t("issue.add.finish_date")}
            value={issue.finish_date}
            onChange={(val) => void updateDates({ finish_date: toPayload(val) })}
            minDate={issue.start_date ? new Date(`${issue.start_date}T00:00:00`) : undefined}
            disabled={disabled}
            buttonVariant="transparent-with-text"
            className="group w-full grow"
            buttonContainerClassName="w-full text-left h-7.5"
            buttonClassName={`${textClassName} ${issue?.finish_date ? "" : "text-placeholder"}`}
            hideIcon
            clearIconClassName="h-3 w-3 hidden group-hover:inline"
          />
        </div>
      </SidebarPropertyListItem>

      <SidebarPropertyListItem icon={DueDatePropertyIcon} label={t("common.order_by.due_date")}>
        <div className="flex w-full items-center gap-2" title={t("issue.dates.help.due")}>
          <DateDropdown
            placeholder={t("issue.add.due_date")}
            value={issue.target_date}
            onChange={(val) => void updateDates({ target_date: toPayload(val) })}
            disabled={disabled}
            buttonVariant="transparent-with-text"
            className="group w-full grow"
            buttonContainerClassName="w-full text-left h-7.5"
            buttonClassName={cn(textClassName, {
              "text-placeholder": !issue.target_date,
              "text-danger-primary": shouldHighlightIssueDueDate(issue.target_date, stateGroup, timeZone),
            })}
            hideIcon
            clearIconClassName="h-3 w-3 hidden group-hover:inline text-primary"
          />
          {issue.target_date && <DateAlert date={issue.target_date} workItem={issue} projectId={projectId} />}
        </div>
      </SidebarPropertyListItem>

      {warnings.length > 0 && (
        <div className="flex items-start gap-2">
          <div className="w-30 shrink-0" />
          <ul className="flex grow flex-col gap-0.5 text-body-xs-regular text-warning-primary">
            {warnings.map((warning) => (
              <li key={warning} className="flex items-center gap-1">
                <AlertTriangle className="size-3 shrink-0" />
                {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      <SidebarPropertyListItem icon={Timer} label={t("duration")}>
        <DurationDropdown
          placeholder={t("issue.add.duration")}
          value={issue.duration}
          onChange={(val) => void updateDates({ duration: val })}
          disabled={disabled}
          buttonVariant="transparent-with-text"
          className="group w-full grow"
          buttonContainerClassName="w-full text-left h-7.5"
          buttonClassName={`${textClassName} ${issue?.duration ? "" : "text-placeholder"}`}
          hideIcon
          clearIconClassName="h-3 w-3 hidden group-hover:inline"
        />
      </SidebarPropertyListItem>
    </>
  );
});
