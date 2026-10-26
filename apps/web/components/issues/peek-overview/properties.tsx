/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Timer } from "lucide-react";
// i18n
import { useTranslation } from "@plane/i18n";
// ui icons
import {
  CyclesOutline,
  DueDateOutline,
  EstimateOutline,
  LabelsOutline,
  MembersOutline,
  ModuleOutline,
  ParentOutline,
  PriorityOutline,
  StartDateOutline,
  StateOutline,
  UserOutline,
} from "@makeplane/propel/icons";
import { DateSelect } from "@/components/dropdowns/date-select";
import {
  cn,
  getDate,
  renderFormattedPayloadDate,
  shouldHighlightIssueDueDate,
  reconcileWorkItemDuration,
} from "@plane/utils";
// components
import { EstimateSelect } from "@/components/dropdowns/estimate/estimate-select";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { PrioritySelect } from "@/components/dropdowns/priority/priority-select";
import { StateSelect } from "@/components/dropdowns/state/state-select";
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
// helpers
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useProjectWeekendDays } from "@/hooks/use-project-weekend-days";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import type { TIssueOperations } from "../issue-detail";
import { IssueCycleSelect } from "../issue-detail/cycle-select";
import { IssueLabel } from "../issue-detail/label";
import { IssueModuleSelect } from "../issue-detail/module-select";
import type { TIssue } from "@plane/types";
import { DurationDropdown } from "@/components/dropdowns/duration";
import { WorkItemAdditionalSidebarProperties } from "@/components/issues/issue-details/additional-properties";
import { IssueParentSelectRoot } from "@/components/issues/issue-details/parent-select-root";
import { DateAlert } from "@/components/issues/issue-details/sidebar/date-alert";
import { TransferHopInfo } from "@/components/issues/issue-details/sidebar/transfer-hop-info";
import { IssueWorklogProperty } from "@/components/issues/worklog/property";

interface IPeekOverviewProperties {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
  issueOperations: TIssueOperations;
}

export const PeekOverviewProperties = observer(function PeekOverviewProperties(props: IPeekOverviewProperties) {
  const { workspaceSlug, projectId, issueId, issueOperations, disabled } = props;
  const { t } = useTranslation();
  // store hooks
  const { getProjectById } = useProject();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { getStateById } = useProjectState();
  const { getUserDetails } = useMember();
  const startOfTheWeek = useStartOfTheWeek();
  // derived values
  const issue = getIssueById(issueId);
  // called before the early return below: hooks run in the same order on every render
  const weekendDays = useProjectWeekendDays(issue?.project_id);
  if (!issue) return <></>;
  const createdByDetails = getUserDetails(issue?.created_by);
  const projectDetails = getProjectById(issue.project_id);
  const isEstimateEnabled = projectDetails?.estimate;
  const stateDetails = getStateById(issue.state_id);

  const updateDurationFields = (change: Partial<Pick<TIssue, "start_date" | "target_date" | "duration">>) =>
    issueOperations.update(workspaceSlug, projectId, issueId, reconcileWorkItemDuration(issue, change, weekendDays));

  return (
    <div>
      <h6 className="text-body-xs-medium">{t("common.properties")}</h6>
      <div className={`mt-3 w-full space-y-3 ${disabled ? "opacity-60" : ""}`}>
        <SidebarPropertyListItem icon={StateOutline} label={t("common.state")}>
          <StateSelect
            testId="work-item-state-select"
            value={issue?.state_id}
            onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { state_id: val })}
            projectId={projectId}
            issueId={issueId}
            filterAvailableStateIds
            disabled={disabled}
            variant="select-ghost-md"
            tooltip
          />
        </SidebarPropertyListItem>

        <SidebarPropertyListItem icon={MembersOutline} label={t("common.assignees")}>
          <MemberSelect
            testId="work-item-assignee-select"
            value={issue?.assignee_ids ?? []}
            onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { assignee_ids: val })}
            disabled={disabled}
            projectId={projectId}
            placeholder={t("issue.add.assignee")}
            multiple
            variant="select-ghost-md"
            showLabel={(issue?.assignee_ids?.length ?? 0) <= 1}
            tooltip={{ heading: t("common.assignees") }}
          />
        </SidebarPropertyListItem>

        <SidebarPropertyListItem icon={PriorityOutline} label={t("common.priority")}>
          <PrioritySelect
            testId="work-item-priority-select"
            value={issue?.priority}
            onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { priority: val })}
            disabled={disabled}
            variant="select-ghost-md"
            tooltip
          />
        </SidebarPropertyListItem>

        {createdByDetails && (
          <SidebarPropertyListItem icon={UserOutline} label={t("common.created_by")} childrenClassName="px-2">
            <ButtonAvatars
              showTooltip
              userIds={createdByDetails?.display_name?.includes("-intake") ? null : createdByDetails?.id}
            />
            <span className="grow truncate text-body-xs-medium leading-5 text-secondary">
              {createdByDetails?.display_name?.includes("-intake") ? "Pi-Plane" : createdByDetails?.display_name}
            </span>
          </SidebarPropertyListItem>
        )}

        <SidebarPropertyListItem icon={StartDateOutline} label={t("common.order_by.start_date")}>
          <DateSelect
            testId="work-item-start-date-select"
            value={getDate(issue.start_date) ?? null}
            onChange={(val) =>
              updateDurationFields({ start_date: val ? (renderFormattedPayloadDate(val) ?? null) : null })
            }
            placeholder={t("issue.add.start_date")}
            disabled={disabled}
            clearable
            weekStartsOn={startOfTheWeek}
            variant="select-ghost-md"
            showTooltip
            tooltipHeading={t("common.order_by.start_date")}
          />
        </SidebarPropertyListItem>

        <SidebarPropertyListItem icon={DueDateOutline} label={t("common.order_by.due_date")}>
          <div className="flex w-full items-center gap-2">
            <DateSelect
              testId="work-item-due-date-select"
              value={getDate(issue.target_date) ?? null}
              onChange={(val) =>
                updateDurationFields({ target_date: val ? (renderFormattedPayloadDate(val) ?? null) : null })
              }
              placeholder={t("issue.add.due_date")}
              disabled={disabled}
              clearable
              className={cn({
                "text-danger-primary": shouldHighlightIssueDueDate(issue.target_date, stateDetails?.group),
              })}
              weekStartsOn={startOfTheWeek}
              variant="select-ghost-md"
              showTooltip
              tooltipHeading={t("common.order_by.due_date")}
            />
            {issue.target_date && <DateAlert date={issue.target_date} workItem={issue} projectId={projectId} />}
          </div>
        </SidebarPropertyListItem>

        <SidebarPropertyListItem icon={Timer} label={t("duration")}>
          <DurationDropdown
            value={issue.duration}
            onChange={(val) => updateDurationFields({ duration: val })}
            placeholder={t("issue.add.duration")}
            variant="select-ghost-md"
            disabled={disabled}
            className="group w-full grow"
            hideIcon
          />
        </SidebarPropertyListItem>

        {isEstimateEnabled && (
          <SidebarPropertyListItem icon={EstimateOutline} label={t("common.estimate")}>
            <EstimateSelect
              value={issue.estimate_point ?? undefined}
              onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { estimate_point: val })}
              projectId={projectId}
              disabled={disabled}
              variant="select-ghost-md"
              placeholder={t("none")}
              tooltip
            />
          </SidebarPropertyListItem>
        )}

        {projectDetails?.module_view && (
          <SidebarPropertyListItem icon={ModuleOutline} label={t("common.modules")}>
            <IssueModuleSelect
              className="w-full grow"
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              issueOperations={issueOperations}
              disabled={disabled}
            />
          </SidebarPropertyListItem>
        )}

        {projectDetails?.cycle_view && (
          <SidebarPropertyListItem
            icon={CyclesOutline}
            label={t("common.cycle")}
            appendElement={<TransferHopInfo workItem={issue} />}
          >
            <IssueCycleSelect
              className="h-7.5 w-full grow"
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              issueOperations={issueOperations}
              disabled={disabled}
            />
          </SidebarPropertyListItem>
        )}

        <SidebarPropertyListItem icon={ParentOutline} label={t("common.parent")}>
          <IssueParentSelectRoot
            className="h-7.5 w-full grow"
            disabled={disabled}
            issueId={issueId}
            issueOperations={issueOperations}
            projectId={projectId}
            workspaceSlug={workspaceSlug}
          />
        </SidebarPropertyListItem>

        <SidebarPropertyListItem icon={LabelsOutline} label={t("common.labels")}>
          <IssueLabel workspaceSlug={workspaceSlug} projectId={projectId} issueId={issueId} disabled={disabled} />
        </SidebarPropertyListItem>

        <IssueWorklogProperty
          workspaceSlug={workspaceSlug}
          projectId={projectId}
          issueId={issueId}
          disabled={disabled}
        />

        <WorkItemAdditionalSidebarProperties
          workItemId={issue.id}
          workItemTypeId={issue.type_id}
          projectId={projectId}
          workspaceSlug={workspaceSlug}
          isEditable={!disabled}
          isPeekView
        />
      </div>
    </div>
  );
});
