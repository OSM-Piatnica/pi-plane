/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Network } from "lucide-react";
// i18n
import { useTranslation } from "@plane/i18n";
// ui
import {
  CyclesOutline,
  EstimateOutline,
  LabelsOutline,
  MembersOutline,
  ModuleOutline,
  ParentOutline,
  PriorityOutline,
  StateOutline,
  UserOutline,
} from "@makeplane/propel/icons";
// components
import { EstimateSelect } from "@/components/dropdowns/estimate/estimate-select";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { WorkItemPlanningDates } from "@/components/issues/work-item-planning-dates";
import { GroupAssigneeSelect } from "@/components/workspace/user-groups/group-assignee-select";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { PrioritySelect } from "@/components/dropdowns/priority/priority-select";
import { StateSelect } from "@/components/dropdowns/state/state-select";
// hooks
import { useProjectEstimates } from "@/hooks/store/estimates";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
// components
import { WorkItemAdditionalSidebarProperties } from "@/components/issues/issue-details/additional-properties";
import { IssueParentSelectRoot } from "@/components/issues/issue-details/parent-select-root";
import { TransferHopInfo } from "@/components/issues/issue-details/sidebar/transfer-hop-info";
import { IssueWorklogProperty } from "@/components/issues/worklog/property";
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { IssueCycleSelect } from "./cycle-select";
import { IssueLabel } from "./label";
import { IssueModuleSelect } from "./module-select";
import type { TIssueOperations } from "./root";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  issueOperations: TIssueOperations;
  isEditable: boolean;
};

export const IssueDetailsSidebar = observer(function IssueDetailsSidebar(props: Props) {
  const { t } = useTranslation();
  const { workspaceSlug, projectId, issueId, issueOperations, isEditable } = props;
  // store hooks
  const { getProjectById } = useProject();
  const { areEstimateEnabledByProjectId } = useProjectEstimates();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { getUserDetails } = useMember();
  const { getStateById } = useProjectState();
  const issue = getIssueById(issueId);
  if (!issue) return <></>;

  const createdByDetails = getUserDetails(issue.created_by);

  // derived values
  const projectDetails = getProjectById(issue.project_id);
  const stateDetails = getStateById(issue.state_id);

  return (
    <>
      <div className="flex h-full w-full flex-col items-center divide-y-2 divide-subtle-1 overflow-hidden">
        <div className="h-full w-full overflow-y-auto px-6">
          <h5 className="mt-5 text-body-xs-medium">{t("common.properties")}</h5>
          <div className={`mt-4 mb-2 space-y-2.5 truncate ${!isEditable ? "opacity-60" : ""}`}>
            <SidebarPropertyListItem icon={StateOutline} label={t("common.state")}>
              <StateSelect
                testId="work-item-state-select"
                value={issue?.state_id}
                onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { state_id: val })}
                projectId={projectId}
                issueId={issueId}
                filterAvailableStateIds
                disabled={!isEditable}
                variant="select-ghost-md"
                tooltip
              />
            </SidebarPropertyListItem>

            <SidebarPropertyListItem icon={MembersOutline} label={t("common.assignees")}>
              <MemberSelect
                testId="work-item-assignee-select"
                value={issue?.assignee_ids ?? []}
                onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { assignee_ids: val })}
                disabled={!isEditable}
                projectId={projectId}
                placeholder={t("issue.add.assignee")}
                multiple
                variant="select-ghost-md"
                showLabel={(issue?.assignee_ids?.length ?? 0) <= 1}
                tooltip={{ heading: t("common.assignees") }}
              />
            </SidebarPropertyListItem>

            <SidebarPropertyListItem icon={Network} label={t("workspace_settings.settings.groups.group_assignees")}>
              <GroupAssigneeSelect
                workspaceSlug={workspaceSlug}
                value={issue?.group_assignee_ids ?? []}
                onChange={(val) =>
                  issueOperations.update(workspaceSlug, projectId, issueId, { group_assignee_ids: val })
                }
                disabled={!isEditable}
              />
            </SidebarPropertyListItem>

            <SidebarPropertyListItem icon={PriorityOutline} label={t("common.priority")}>
              <PrioritySelect
                testId="work-item-priority-select"
                value={issue?.priority}
                onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { priority: val })}
                disabled={!isEditable}
                variant="select-ghost-md"
                tooltip
              />
            </SidebarPropertyListItem>

            {createdByDetails && (
              <SidebarPropertyListItem icon={UserOutline} label={t("common.created_by")}>
                <div className="flex gap-2 px-2">
                  <ButtonAvatars showTooltip userIds={createdByDetails.id} />
                  <span className="grow truncate text-body-xs-regular leading-5">{createdByDetails?.display_name}</span>
                </div>
              </SidebarPropertyListItem>
            )}

            <WorkItemPlanningDates
              issue={issue}
              projectId={projectId}
              stateGroup={stateDetails?.group}
              disabled={!isEditable}
              onUpdate={(data) => issueOperations.update(workspaceSlug, projectId, issueId, data)}
            />

            {projectId && areEstimateEnabledByProjectId(projectId) && (
              <SidebarPropertyListItem icon={EstimateOutline} label={t("common.estimate")}>
                <EstimateSelect
                  value={issue?.estimate_point ?? undefined}
                  onChange={(val: string | null) =>
                    issueOperations.update(workspaceSlug, projectId, issueId, { estimate_point: val })
                  }
                  projectId={projectId}
                  disabled={!isEditable}
                  variant="select-ghost-md"
                  placeholder={t("common.none")}
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
                  disabled={!isEditable}
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
                  disabled={!isEditable}
                />
              </SidebarPropertyListItem>
            )}

            <SidebarPropertyListItem icon={ParentOutline} label={t("common.parent")}>
              <IssueParentSelectRoot
                className="h-7.5 w-full grow"
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                issueId={issueId}
                issueOperations={issueOperations}
                disabled={!isEditable}
              />
            </SidebarPropertyListItem>

            <SidebarPropertyListItem icon={LabelsOutline} label={t("common.labels")}>
              <IssueLabel
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                issueId={issueId}
                disabled={!isEditable}
              />
            </SidebarPropertyListItem>

            <IssueWorklogProperty
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              disabled={!isEditable}
            />

            <WorkItemAdditionalSidebarProperties
              workItemId={issue.id}
              workItemTypeId={issue.type_id}
              projectId={projectId}
              workspaceSlug={workspaceSlug}
              isEditable={isEditable}
            />
          </div>
        </div>
      </div>
    </>
  );
});
