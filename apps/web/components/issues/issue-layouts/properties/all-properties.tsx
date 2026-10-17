/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

/* eslint-disable jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions, unicorn/consistent-function-scoping */

import type { SyntheticEvent } from "react";
import { useCallback, useMemo } from "react";
import { xor } from "lodash-es";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// icons
import { AttachOutline, DueDateOutline, LinkOutline, StartDateOutline, ViewsOutline } from "@makeplane/propel/icons";
// i18n
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { DateRangeValue } from "@plane/blocks/property-select";
import { DateRangeSelect, DateSelect } from "@/components/dropdowns/date-select";
import type { TIssue, IIssueDisplayProperties, TIssuePriorities } from "@plane/types";
// ui
import {
  cn,
  getDate,
  renderFormattedPayloadDate,
  generateWorkItemLink,
  shouldHighlightIssueDueDate,
} from "@plane/utils";
// components
import { CycleSelect } from "@/components/dropdowns/cycle/cycle-select";
import { EstimateSelect } from "@/components/dropdowns/estimate/estimate-select";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { ModuleSelect } from "@/components/dropdowns/module/module-select";
import { PrioritySelect } from "@/components/dropdowns/priority/priority-select";
import { StateSelect } from "@/components/dropdowns/state/state-select";
import { getIssueApiErrorMessage } from "@/helpers/issue-api-error";
// hooks
import { useProjectEstimates } from "@/hooks/store/estimates";
import { useIssues } from "@/hooks/store/use-issues";
import { useLabel } from "@/hooks/store/use-label";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useUserProfile } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { WorkItemLayoutAdditionalProperties } from "@/components/issues/issue-layouts/additional-properties";
// local components
import { IssuePropertyLabels } from "./labels";
import { WithDisplayPropertiesHOC } from "./with-display-properties-HOC";
import { Timer } from "lucide-react";
import { setToast } from "@plane/blocks/toast";

const handleEventPropagation = (e: SyntheticEvent<Element>) => {
  e.stopPropagation();
  e.preventDefault();
};

export interface IIssueProperties {
  issue: TIssue;
  updateIssue: ((projectId: string | null, issueId: string, data: Partial<TIssue>) => Promise<void>) | undefined;
  displayProperties: IIssueDisplayProperties | undefined;
  isReadOnly: boolean;
  className: string;
  activeLayout: string;
  isEpic?: boolean;
}

export const IssueProperties = observer(function IssueProperties(props: IIssueProperties) {
  const { issue, updateIssue, displayProperties, isReadOnly, className, isEpic = false } = props;
  // i18n
  const { t } = useTranslation();
  // store hooks
  const { getProjectById } = useProject();
  const { labelMap } = useLabel();
  const storeType = useIssueStoreType();
  const {
    issues: { changeModulesInIssue },
  } = useIssues(storeType);
  const {
    issues: { addCycleToIssue, removeCycleFromIssue },
  } = useIssues(storeType);
  const { areEstimateEnabledByProjectId } = useProjectEstimates();
  const { getStateById } = useProjectState();
  const { data: userProfile } = useUserProfile();
  const { isMobile } = usePlatformOS();
  const projectDetails = getProjectById(issue.project_id);

  // router
  const router = useAppRouter();
  const { workspaceSlug, projectId } = useParams();

  // derived values
  const stateDetails = getStateById(issue.state_id);
  const subIssueCount = issue?.sub_issues_count ?? 0;
  const durationLabel =
    issue.duration === null || issue.duration === undefined ? null : t("duration_days", { count: issue.duration });

  const issueOperations = useMemo(
    () => ({
      addModulesToIssue: async (moduleIds: string[]) => {
        if (!workspaceSlug || !issue.project_id || !issue.id) return;
        await changeModulesInIssue?.(workspaceSlug.toString(), issue.project_id, issue.id, moduleIds, []);
      },
      removeModulesFromIssue: async (moduleIds: string[]) => {
        if (!workspaceSlug || !issue.project_id || !issue.id) return;
        await changeModulesInIssue?.(workspaceSlug.toString(), issue.project_id, issue.id, [], moduleIds);
      },
      addIssueToCycle: async (cycleId: string) => {
        if (!workspaceSlug || !issue.project_id || !issue.id) return;
        await addCycleToIssue?.(workspaceSlug.toString(), issue.project_id, cycleId, issue.id);
      },
      removeIssueFromCycle: async () => {
        if (!workspaceSlug || !issue.project_id || !issue.id) return;
        await removeCycleFromIssue?.(workspaceSlug.toString(), issue.project_id, issue.id);
      },
    }),
    [workspaceSlug, issue, changeModulesInIssue, addCycleToIssue, removeCycleFromIssue]
  );

  const handleState = async (stateId: string) => {
    if (!updateIssue) return;
    try {
      await updateIssue(issue.project_id, issue.id, { state_id: stateId });
    } catch (error) {
      setToast({
        type: "error",
        title: t("common.error.label"),
        message: getIssueApiErrorMessage(error, t("entity.update.failed", { entity: t("issue.label") }), t),
      });
    }
  };

  const handlePriority = async (value: TIssuePriorities) => {
    if (updateIssue) await updateIssue(issue.project_id, issue.id, { priority: value });
  };

  const handleLabel = async (ids: string[]) => {
    if (updateIssue) await updateIssue(issue.project_id, issue.id, { label_ids: ids });
  };

  const handleAssignee = async (ids: string[]) => {
    if (updateIssue) await updateIssue(issue.project_id, issue.id, { assignee_ids: ids });
  };

  const handleModule = useCallback(
    (moduleIds: string[] | null) => {
      if (!issue || !issue.module_ids || !moduleIds) return;

      const updatedModuleIds = xor(issue.module_ids, moduleIds);
      const modulesToAdd: string[] = [];
      const modulesToRemove: string[] = [];
      for (const moduleId of updatedModuleIds)
        if (issue.module_ids.includes(moduleId)) modulesToRemove.push(moduleId);
        else modulesToAdd.push(moduleId);
      if (modulesToAdd.length > 0) issueOperations.addModulesToIssue(modulesToAdd);
      if (modulesToRemove.length > 0) issueOperations.removeModulesFromIssue(modulesToRemove);
    },
    [issueOperations, issue]
  );

  const handleCycle = useCallback(
    (cycleId: string | null) => {
      if (!issue || issue.cycle_id === cycleId) return;
      if (cycleId) issueOperations.addIssueToCycle?.(cycleId);
      else issueOperations.removeIssueFromCycle?.();
    },
    [issue, issueOperations]
  );

  const handleStartDate = async (date: Date | null) => {
    if (!updateIssue) return;
    try {
      await updateIssue(issue.project_id, issue.id, { start_date: date ? renderFormattedPayloadDate(date) : null });
    } catch (error) {
      setToast({
        type: "error",
        title: t("common.error.label"),
        message: getIssueApiErrorMessage(error, t("entity.update.failed", { entity: t("issue.label") }), t),
      });
    }
  };

  const handleTargetDate = async (date: Date | null) => {
    if (!updateIssue) return;
    try {
      await updateIssue(issue.project_id, issue.id, { target_date: date ? renderFormattedPayloadDate(date) : null });
    } catch (error) {
      setToast({
        type: "error",
        title: t("common.error.label"),
        message: getIssueApiErrorMessage(error, t("entity.update.failed", { entity: t("issue.label") }), t),
      });
    }
  };

  const handleDateRangeUpdate = async (range: DateRangeValue) => {
    if (updateIssue)
      await updateIssue(issue.project_id, issue.id, {
        start_date: range.from ? renderFormattedPayloadDate(range.from) : null,
        target_date: range.to ? renderFormattedPayloadDate(range.to) : null,
      });
  };

  const handleEstimate = async (value: string | null) => {
    if (updateIssue) await updateIssue(issue.project_id, issue.id, { estimate_point: value });
  };

  const workItemLink = generateWorkItemLink({
    workspaceSlug: workspaceSlug?.toString(),
    projectId: issue?.project_id,
    issueId: issue?.id,
    projectIdentifier: projectDetails?.identifier,
    sequenceId: issue?.sequence_id,
    isArchived: !!issue?.archived_at,
    isEpic,
  });

  const redirectToIssueDetail = () => router.push(`${workItemLink}#sub-issues`);

  if (!displayProperties || !issue.project_id) return null;

  // date range is enabled only when both dates are available and both dates are enabled
  const isDateRangeEnabled: boolean = Boolean(
    issue.start_date && issue.target_date && displayProperties.start_date && displayProperties.due_date
  );

  const defaultLabelOptions =
    issue?.label_ids?.flatMap((id) => {
      const label = labelMap[id];
      return label ? [label] : [];
    }) || [];

  const minDate = getDate(issue.start_date);
  const maxDate = getDate(issue.target_date);

  return (
    <div className={className}>
      {/* basic properties */}
      {/* state */}
      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="state">
        <div
          className="h-5"
          role="presentation"
          onFocus={handleEventPropagation}
          onClick={handleEventPropagation}
          onKeyDown={handleEventPropagation}
        >
          <StateSelect
            value={issue.state_id}
            onChange={handleState}
            projectId={issue.project_id}
            issueId={issue.id}
            filterAvailableStateIds
            disabled={isReadOnly}
            variant="pill-sm"
            tooltip
          />
        </div>
      </WithDisplayPropertiesHOC>

      {/* priority */}
      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="priority">
        <div
          className="h-5"
          role="presentation"
          onFocus={handleEventPropagation}
          onClick={handleEventPropagation}
          onKeyDown={handleEventPropagation}
        >
          <PrioritySelect
            value={issue?.priority}
            onChange={handlePriority}
            disabled={isReadOnly}
            variant="pill-sm"
            tooltip
          />
        </div>
      </WithDisplayPropertiesHOC>

      {/* merged dates */}
      <WithDisplayPropertiesHOC
        displayProperties={displayProperties}
        displayPropertyKey={["start_date", "due_date"]}
        shouldRenderProperty={() => isDateRangeEnabled}
      >
        <div
          className="h-5"
          role="presentation"
          onFocus={handleEventPropagation}
          onClick={handleEventPropagation}
          onKeyDown={handleEventPropagation}
        >
          <DateRangeSelect
            value={{
              from: getDate(issue.start_date) ?? null,
              to: getDate(issue.target_date) ?? null,
            }}
            onChange={handleDateRangeUpdate}
            icon={<StartDateOutline />}
            clearable
            mergeDates
            className={cn({
              "text-danger-primary": shouldHighlightIssueDueDate(issue.target_date, stateDetails?.group),
            })}
            disabled={isReadOnly}
            showTooltip
            tooltipHeading={t("project_cycles.date_range")}
            weekStartsOn={userProfile?.start_of_the_week}
            variant="pill-sm"
          />
        </div>
      </WithDisplayPropertiesHOC>

      {/* start date */}
      <WithDisplayPropertiesHOC
        displayProperties={displayProperties}
        displayPropertyKey="start_date"
        shouldRenderProperty={() => !isDateRangeEnabled}
      >
        <div
          className="h-5"
          role="presentation"
          onFocus={handleEventPropagation}
          onClick={handleEventPropagation}
          onKeyDown={handleEventPropagation}
        >
          <DateSelect
            value={getDate(issue.start_date) ?? null}
            onChange={handleStartDate}
            maxDate={maxDate}
            placeholder={t("common.order_by.start_date")}
            icon={<StartDateOutline />}
            clearable
            disabled={isReadOnly}
            showTooltip
            tooltipHeading={t("common.order_by.start_date")}
            weekStartsOn={userProfile?.start_of_the_week}
            variant="pill-sm"
          />
        </div>
      </WithDisplayPropertiesHOC>

      {/* target/due date */}
      <WithDisplayPropertiesHOC
        displayProperties={displayProperties}
        displayPropertyKey="due_date"
        shouldRenderProperty={() => !isDateRangeEnabled}
      >
        <div
          className="h-5"
          role="presentation"
          onFocus={handleEventPropagation}
          onClick={handleEventPropagation}
          onKeyDown={handleEventPropagation}
        >
          <DateSelect
            value={getDate(issue?.target_date) ?? null}
            onChange={handleTargetDate}
            minDate={minDate}
            placeholder={t("common.order_by.due_date")}
            icon={<DueDateOutline />}
            className={cn({
              "text-danger-primary": shouldHighlightIssueDueDate(issue.target_date, stateDetails?.group),
            })}
            clearable
            disabled={isReadOnly}
            showTooltip
            tooltipHeading={t("common.order_by.due_date")}
            weekStartsOn={userProfile?.start_of_the_week}
            variant="pill-sm"
          />
        </div>
      </WithDisplayPropertiesHOC>

      {/* duration */}
      <WithDisplayPropertiesHOC
        displayProperties={displayProperties}
        displayPropertyKey="duration"
        shouldRenderProperty={(properties) => !!properties.duration && !!durationLabel}
      >
        <Tooltip label={`${t("duration")}: ${durationLabel}`} disabled={isMobile}>
          <div
            role="presentation"
            className="flex h-5 flex-shrink-0 items-center justify-center gap-2 overflow-hidden rounded-sm border-[0.5px] border-strong px-2.5 py-1"
            onFocus={handleEventPropagation}
            onClick={handleEventPropagation}
            onKeyDown={handleEventPropagation}
          >
            <Timer className="h-3 w-3 flex-shrink-0" strokeWidth={2} />
            <div className="text-caption-sm-regular">{durationLabel}</div>
          </div>
        </Tooltip>
      </WithDisplayPropertiesHOC>

      {/* assignee */}
      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="assignee">
        <div
          className="h-5"
          role="presentation"
          onFocus={handleEventPropagation}
          onClick={handleEventPropagation}
          onKeyDown={handleEventPropagation}
        >
          <MemberSelect
            projectId={issue?.project_id ?? undefined}
            value={issue?.assignee_ids ?? []}
            onChange={handleAssignee}
            disabled={isReadOnly}
            multiple
            variant={issue.assignee_ids?.length ? "avatar-group-sm" : "pill-sm"}
            placeholder={t("common.assignees")}
            tooltip={{ heading: t("common.assignees") }}
          />
        </div>
      </WithDisplayPropertiesHOC>

      <>
        {!isEpic && (
          <>
            {/* modules */}
            {projectDetails?.module_view && (
              <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="modules">
                <div
                  className="h-5"
                  role="presentation"
                  onFocus={handleEventPropagation}
                  onClick={handleEventPropagation}
                  onKeyDown={handleEventPropagation}
                >
                  <ModuleSelect
                    multiple
                    projectId={issue?.project_id ?? undefined}
                    value={issue?.module_ids ?? []}
                    onChange={handleModule}
                    disabled={isReadOnly}
                    variant="pill-sm"
                    tooltip
                  />
                </div>
              </WithDisplayPropertiesHOC>
            )}

            {/* cycles */}
            {projectDetails?.cycle_view && (
              <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="cycle">
                <div
                  className="h-5"
                  role="presentation"
                  onFocus={handleEventPropagation}
                  onClick={handleEventPropagation}
                  onKeyDown={handleEventPropagation}
                >
                  <CycleSelect
                    projectId={issue?.project_id ?? undefined}
                    value={issue?.cycle_id}
                    onChange={handleCycle}
                    disabled={isReadOnly}
                    variant="pill-sm"
                    tooltip
                  />
                </div>
              </WithDisplayPropertiesHOC>
            )}
          </>
        )}
      </>

      {/* estimates */}
      {projectId && areEstimateEnabledByProjectId(projectId?.toString()) && (
        <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="estimate">
          <div
            className="h-5"
            role="presentation"
            onFocus={handleEventPropagation}
            onClick={handleEventPropagation}
            onKeyDown={handleEventPropagation}
          >
            <EstimateSelect
              value={issue.estimate_point ?? undefined}
              onChange={handleEstimate}
              projectId={issue.project_id}
              disabled={isReadOnly}
              variant="pill-sm"
              tooltip
            />
          </div>
        </WithDisplayPropertiesHOC>
      )}

      {/* extra render properties */}
      {/* sub-issues */}
      {!isEpic && (
        <WithDisplayPropertiesHOC
          displayProperties={displayProperties}
          displayPropertyKey="sub_issue_count"
          shouldRenderProperty={(properties) => !!properties.sub_issue_count && !!subIssueCount}
        >
          <Tooltip label={`${t("common.sub_work_items")}: ${subIssueCount}`} disabled={isMobile}>
            <button
              type="button"
              onFocus={handleEventPropagation}
              onClick={(e) => {
                e.stopPropagation();
                e.preventDefault();
                if (subIssueCount) redirectToIssueDetail();
              }}
              className={cn(
                "flex h-5 flex-shrink-0 items-center justify-center gap-2 overflow-hidden rounded-sm border-[0.5px] border-strong px-2.5 py-1",
                {
                  "cursor-pointer hover:bg-layer-1": subIssueCount,
                }
              )}
            >
              <ViewsOutline className="h-3 w-3 flex-shrink-0" />
              <div className="text-caption-sm-regular">{subIssueCount}</div>
            </button>
          </Tooltip>
        </WithDisplayPropertiesHOC>
      )}

      {/* attachments */}
      <WithDisplayPropertiesHOC
        displayProperties={displayProperties}
        displayPropertyKey="attachment_count"
        shouldRenderProperty={(properties) => !!properties.attachment_count && !!issue.attachment_count}
      >
        <Tooltip label={`${t("common.attachments")}: ${issue.attachment_count}`} disabled={isMobile}>
          <div
            role="presentation"
            className="flex h-5 flex-shrink-0 items-center justify-center gap-2 overflow-hidden rounded-sm border-[0.5px] border-strong px-2.5 py-1"
            onFocus={handleEventPropagation}
            onClick={handleEventPropagation}
            onKeyDown={handleEventPropagation}
          >
            <AttachOutline className="h-3 w-3 flex-shrink-0" />
            <div className="text-caption-sm-regular">{issue.attachment_count}</div>
          </div>
        </Tooltip>
      </WithDisplayPropertiesHOC>

      {/* link */}
      <WithDisplayPropertiesHOC
        displayProperties={displayProperties}
        displayPropertyKey="link"
        shouldRenderProperty={(properties) => !!properties.link && !!issue.link_count}
      >
        <Tooltip label={`${t("common.links")}: ${issue.link_count}`} disabled={isMobile}>
          <div
            role="presentation"
            className="flex h-5 flex-shrink-0 items-center justify-center gap-2 overflow-hidden rounded-sm border-[0.5px] border-strong px-2.5 py-1"
            onFocus={handleEventPropagation}
            onClick={handleEventPropagation}
            onKeyDown={handleEventPropagation}
          >
            <LinkOutline className="h-3 w-3 flex-shrink-0" />
            <div className="text-caption-sm-regular">{issue.link_count}</div>
          </div>
        </Tooltip>
      </WithDisplayPropertiesHOC>

      {/* Additional Properties */}
      <WorkItemLayoutAdditionalProperties displayProperties={displayProperties} issue={issue} />

      {/* label */}
      <WithDisplayPropertiesHOC displayProperties={displayProperties} displayPropertyKey="labels">
        <IssuePropertyLabels
          projectId={issue?.project_id || null}
          value={issue?.label_ids || []}
          defaultOptions={defaultLabelOptions}
          onChange={handleLabel}
          disabled={isReadOnly}
          renderByDefault={isMobile}
          hideDropdownArrow
          maxRender={3}
        />
      </WithDisplayPropertiesHOC>
    </div>
  );
});
