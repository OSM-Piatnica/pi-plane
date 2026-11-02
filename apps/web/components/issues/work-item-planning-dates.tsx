/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { AlertTriangle, Timer } from "lucide-react";
// plane imports
import { DueDateOutline, StartDateOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { TIssue, TStateGroups } from "@plane/types";
import { cn, getDate, renderFormattedPayloadDate, shouldHighlightIssueDueDate } from "@plane/utils";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { DateSelect } from "@/components/dropdowns/date-select";
import { DurationDropdown } from "@/components/dropdowns/duration";
import { DateAlert } from "@/components/issues/issue-details/sidebar/date-alert";
// hooks
import { useProjectWeekendDays } from "@/hooks/use-project-weekend-days";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { useProjectTimeZone, useWorkItemDateEdit, useWorkItemDateStatuses } from "@/hooks/use-work-item-dates";

type Props = {
  issue: TIssue;
  projectId: string;
  stateGroup: TStateGroups | undefined;
  disabled?: boolean;
  /** Existing save operation of the surface (optimistic update, rollback and error toast stay there). */
  onUpdate: (data: Partial<TIssue>) => Promise<void> | void;
};

/**
 * Start, finish, due and duration of a work item, side by side and independently editable.
 * - Finish is the planned end of the work and drives the duration.
 * - Due is a deadline. It is never moved by, nor does it move, the schedule.
 */
export const WorkItemPlanningDates = observer(function WorkItemPlanningDates(props: Props) {
  const { issue, projectId, stateGroup, disabled, onUpdate } = props;
  const { t } = useTranslation();
  const startOfTheWeek = useStartOfTheWeek();
  const weekendDays = useProjectWeekendDays(issue.project_id ?? projectId);
  const timeZone = useProjectTimeZone(projectId);
  const isActive = stateGroup !== "completed" && stateGroup !== "cancelled";
  const statuses = useWorkItemDateStatuses(issue, isActive, projectId);
  const updateDates = useWorkItemDateEdit(issue, onUpdate, weekendDays);

  const toPayload = (date: Date | null | undefined) => (date ? (renderFormattedPayloadDate(date) ?? null) : null);

  const warnings = [
    statuses.overdue && t("issue.dates.status.overdue"),
    statuses.forecastMissesDeadline && t("issue.dates.status.forecast_misses_deadline"),
    statuses.plannedFinishPassed && t("issue.dates.status.planned_finish_passed"),
    statuses.completedLate && t("issue.dates.status.completed_late"),
  ].filter(Boolean) as string[];

  return (
    <>
      <SidebarPropertyListItem icon={StartDateOutline} label={t("common.order_by.start_date")}>
        <DateSelect
          testId="work-item-start-date-select"
          placeholder={t("issue.add.start_date")}
          value={getDate(issue.start_date) ?? null}
          onChange={(val) => void updateDates({ start_date: toPayload(val) })}
          disabled={disabled}
          clearable
          weekStartsOn={startOfTheWeek}
          variant="select-ghost-md"
          showTooltip
          tooltipHeading={t("common.order_by.start_date")}
        />
      </SidebarPropertyListItem>

      <SidebarPropertyListItem icon={DueDateOutline} label={t("common.order_by.finish_date")}>
        <div className="w-full" title={t("issue.dates.help.finish")}>
          <DateSelect
            testId="work-item-finish-date-select"
            placeholder={t("issue.add.finish_date")}
            value={getDate(issue.finish_date) ?? null}
            onChange={(val) => void updateDates({ finish_date: toPayload(val) })}
            minDate={getDate(issue.start_date) ?? undefined}
            disabled={disabled}
            clearable
            weekStartsOn={startOfTheWeek}
            variant="select-ghost-md"
            showTooltip
            tooltipHeading={t("common.order_by.finish_date")}
          />
        </div>
      </SidebarPropertyListItem>

      <SidebarPropertyListItem icon={DueDateOutline} label={t("common.order_by.due_date")}>
        <div className="flex w-full items-center gap-2" title={t("issue.dates.help.due")}>
          <DateSelect
            testId="work-item-due-date-select"
            placeholder={t("issue.add.due_date")}
            value={getDate(issue.target_date) ?? null}
            onChange={(val) => void updateDates({ target_date: toPayload(val) })}
            disabled={disabled}
            clearable
            className={cn({
              "text-danger-primary": shouldHighlightIssueDueDate(issue.target_date, stateGroup, timeZone),
            })}
            weekStartsOn={startOfTheWeek}
            variant="select-ghost-md"
            showTooltip
            tooltipHeading={t("common.order_by.due_date")}
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
          variant="select-ghost-md"
          className="group w-full grow"
          hideIcon
        />
      </SidebarPropertyListItem>
    </>
  );
});
