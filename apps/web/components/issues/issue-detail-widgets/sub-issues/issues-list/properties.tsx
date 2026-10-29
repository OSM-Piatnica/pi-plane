/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import { useMemo } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { DueDateOutline, StartDateOutline } from "@makeplane/propel/icons";
import { DateSelect } from "@/components/dropdowns/date-select";
import type { IIssueDisplayProperties, TIssue } from "@plane/types";
import { cn, getDate, renderFormattedPayloadDate, shouldHighlightIssueDueDate } from "@plane/utils";
// components
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { PrioritySelect } from "@/components/dropdowns/priority/priority-select";
import { StateSelect } from "@/components/dropdowns/state/state-select";
// hooks
import { WithDisplayPropertiesHOC } from "@/components/issues/issue-layouts/properties/with-display-properties-HOC";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";

type Props = {
  workspaceSlug: string;
  parentIssueId: string;
  issueId: string;
  canEdit: boolean;
  updateSubIssue: (
    workspaceSlug: string,
    projectId: string,
    parentIssueId: string,
    issueId: string,
    issueData: Partial<TIssue>,
    oldIssue?: Partial<TIssue>
  ) => Promise<void>;
  displayProperties?: IIssueDisplayProperties;
  issue: TIssue;
};

export const SubIssuesListItemProperties = observer(function SubIssuesListItemProperties(props: Props) {
  const { workspaceSlug, parentIssueId, issueId, canEdit, updateSubIssue, displayProperties, issue } = props;
  const { t } = useTranslation();
  const { getStateById } = useProjectState();
  const startOfTheWeek = useStartOfTheWeek();

  const handleStartDate = (date: Date | null) => {
    if (issue.project_id) {
      updateSubIssue(workspaceSlug, issue.project_id, parentIssueId, issueId, {
        start_date: date ? renderFormattedPayloadDate(date) : null,
      });
    }
  };

  const handleTargetDate = (date: Date | null) => {
    if (issue.project_id) {
      updateSubIssue(workspaceSlug, issue.project_id, parentIssueId, issueId, {
        target_date: date ? renderFormattedPayloadDate(date) : null,
      });
    }
  };

  //derived values
  const stateDetails = useMemo(() => getStateById(issue.state_id), [getStateById, issue.state_id]);
  const shouldHighlight = useMemo(
    () => shouldHighlightIssueDueDate(issue.target_date, stateDetails?.group),
    [issue.target_date, stateDetails?.group]
  );
  if (!displayProperties) return <></>;

  // Start may not pass the planned finish. The due date is a deadline and is not bounded by the schedule.
  const maxDate = getDate(issue.finish_date);

  return (
    <div className="relative flex items-center gap-2">
      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="state">
        <StateSelect
          value={issue.state_id}
          projectId={issue.project_id ?? undefined}
          onChange={(val) =>
            issue.project_id &&
            updateSubIssue(
              workspaceSlug,
              issue.project_id,
              parentIssueId,
              issueId,
              {
                state_id: val,
              },
              { ...issue }
            )
          }
          disabled={!canEdit}
          variant="pill-sm"
          tooltip
        />
      </WithDisplayPropertiesHOC>

      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="priority">
        <PrioritySelect
          value={issue.priority}
          onChange={(val) =>
            issue.project_id &&
            updateSubIssue(workspaceSlug, issue.project_id, parentIssueId, issueId, {
              priority: val,
            })
          }
          disabled={!canEdit}
          variant="pill-sm"
          tooltip
        />
      </WithDisplayPropertiesHOC>

      {/* start date */}
      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="start_date">
        <DateSelect
          value={getDate(issue.start_date) ?? null}
          onChange={handleStartDate}
          maxDate={maxDate}
          placeholder={t("common.order_by.start_date")}
          icon={<StartDateOutline />}
          clearable
          disabled={!canEdit}
          showTooltip
          tooltipHeading={t("common.order_by.start_date")}
          weekStartsOn={startOfTheWeek}
          side="top"
          align="end"
          variant="pill-sm"
        />
      </WithDisplayPropertiesHOC>

      {/* target/due date */}
      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="due_date">
        <DateSelect
          value={getDate(issue?.target_date) ?? null}
          onChange={handleTargetDate}
          placeholder={t("common.order_by.due_date")}
          icon={<DueDateOutline />}
          className={cn({ "text-danger-primary": shouldHighlight })}
          clearable
          disabled={!canEdit}
          showTooltip
          tooltipHeading={t("common.order_by.due_date")}
          weekStartsOn={startOfTheWeek}
          side="top"
          align="end"
          variant="pill-sm"
        />
      </WithDisplayPropertiesHOC>

      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="assignee">
        <MemberSelect
          value={issue.assignee_ids ?? []}
          projectId={issue.project_id ?? undefined}
          onChange={(val) =>
            issue.project_id &&
            updateSubIssue(workspaceSlug, issue.project_id, parentIssueId, issueId, {
              assignee_ids: val,
            })
          }
          disabled={!canEdit}
          multiple
          variant={issue.assignee_ids?.length ? "avatar-group-sm" : "pill-sm"}
          tooltip={{ heading: t("common.assignees") }}
        />
      </WithDisplayPropertiesHOC>
    </div>
  );
});
