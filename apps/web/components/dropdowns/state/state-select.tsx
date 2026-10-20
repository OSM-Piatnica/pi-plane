/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { StateSelect as StateSelectBlock } from "@plane/blocks/property-select";
import type { StateOption } from "@plane/blocks/property-select";
import type { SelectPaginationParams, SelectTooltip, SelectTooltipOverride, SelectVariant } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import { getStateName } from "@plane/utils";
import type { IState, TPaginatedResponse } from "@plane/types";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useWorkflow } from "@/hooks/store/use-workflow";

type StateSelectWebProps = {
  /** Project whose states are offered. */
  projectId: string | undefined;
  /** Current state id (`null` / `undefined` when none). */
  value: string | null | undefined;
  /** Emits the next state id. */
  onChange: (stateId: string) => void;
  variant: SelectVariant;
  disabled?: boolean;
  placeholder?: string;
  onClose?: () => void;
  className?: string;
  tooltip?: SelectTooltip;
  appendElement?: ReactNode;
  /** Forwarded to the block's trigger — see `StateSelectProps["testId"]` doc comment. */
  testId?: string;
  /** Tab order of the trigger, for forms that sequence focus explicitly (`ETabIndices`). */
  tabIndex?: number;
  /** Fork: work item whose workflow decides which target states are offered. */
  issueId?: string;
  /** Fork: only offer the states the workflow allows the work item to move to. */
  filterAvailableStateIds?: boolean;
  /** Fork: the select is used while creating a work item (workflow limits the initial states). */
  isForWorkItemCreation?: boolean;
  /** Fork: ignore the project workflow (e.g. admin or bulk flows). */
  alwaysAllowStateChange?: boolean;
};

const toOption = (state: IState, t: (key: string) => string): StateOption => ({
  id: state.id,
  name: getStateName(state.name, t),
  color: state.color,
  group: state.group,
  order: state.order,
});

/**
 * Web binding for the presentational `StateSelect` block. Resolves the project's states from the
 * project-state store (fetched on first open when the project has not been loaded yet), filters them
 * by the search query and maps the selected id to a `StateOption`.
 *
 * CE change: EE reads a paginated state "lite" resource with workflow gating (`typeId`,
 * `isForWorkItemCreation`, `scopedProjectIds`); CE has neither, so the whole project list is served
 * as one page.
 *
 * Fork change: the fork's project workflows gate the offered states (see `useWorkflow`):
 * `isForWorkItemCreation` limits the initial states, `filterAvailableStateIds` (+ `issueId`) offers only
 * the states the workflow allows the work item to move to. The result is passed to the block as
 * `allowedStateIds`.
 */
export const StateSelect = observer(function StateSelect(props: StateSelectWebProps) {
  const {
    projectId,
    value,
    onChange,
    variant,
    disabled,
    placeholder,
    onClose,
    className,
    tooltip,
    appendElement,
    testId,
    tabIndex,
    issueId,
    filterAvailableStateIds = false,
    isForWorkItemCreation = false,
    alwaysAllowStateChange = false,
  } = props;
  // router params
  const { workspaceSlug } = useParams();
  // store hooks
  const { getProjectStateIds, getStateById, fetchProjectStates } = useProjectState();
  const workflowStore = useWorkflow();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  // translation
  const { t } = useTranslation();
  const resolvedTooltip = useMemo<SelectTooltipOverride | undefined>(() => {
    if (!tooltip) return undefined;
    const override = typeof tooltip === "object" ? tooltip : undefined;
    return {
      heading: override?.heading ?? t("common.state"),
      emptyContent: override?.emptyContent ?? t("common.none"),
    };
  }, [tooltip, t]);

  const isWorkflowActive = Boolean(projectId) && workflowStore.isWorkflowEnabledForProject(projectId);

  // load the work item's workflow status so the allowed target states are known
  useEffect(() => {
    if (!workspaceSlug || !projectId || !issueId || !filterAvailableStateIds || !isWorkflowActive) return;
    void workflowStore.fetchIssueWorkflowStatus(workspaceSlug.toString(), projectId, issueId);
  }, [workspaceSlug, projectId, issueId, filterAvailableStateIds, isWorkflowActive, workflowStore]);

  const getValues = useCallback(
    async ({ search }: SelectPaginationParams): Promise<TPaginatedResponse<StateOption[]>> => {
      if (!workspaceSlug || !projectId) return { results: [] };
      let stateIds = getProjectStateIds(projectId);
      if (!stateIds) {
        await fetchProjectStates(workspaceSlug.toString(), projectId);
        stateIds = getProjectStateIds(projectId);
      }
      if (filterAvailableStateIds && workflowStore.isWorkflowEnabledForProject(projectId)) {
        if (!workflowStore.fetchedMap[projectId]) {
          await workflowStore.fetchProjectWorkflowStates(workspaceSlug.toString(), projectId);
        }
      }
      const query = search?.trim().toLowerCase();
      const results = (stateIds ?? [])
        .map((stateId) => getStateById(stateId))
        .filter((state): state is IState => !!state)
        .map((state) => toOption(state, t))
        .filter((option) => !query || option.name.toLowerCase().includes(query));
      return { results, next_page_results: false };
    },
    [
      workspaceSlug,
      projectId,
      filterAvailableStateIds,
      workflowStore,
      getProjectStateIds,
      fetchProjectStates,
      getStateById,
      t,
    ]
  );

  // Resolved in the observer render (not in a memo) so MobX re-renders when the state loads.
  const selectedState = value ? getStateById(value) : undefined;
  const selected = selectedState ? toOption(selectedState, t) : null;

  // States the workflow allows (null = no restriction).
  const issue = issueId ? getIssueById(issueId) : undefined;
  const currentStateId = issue?.state_id ?? value ?? undefined;
  let allowedStateIds: Set<string> | null = null;
  if (projectId && isWorkflowActive && !alwaysAllowStateChange) {
    if (isForWorkItemCreation) {
      const stateIds = getProjectStateIds(projectId) ?? [];
      allowedStateIds = new Set(
        stateIds.filter((stateId) => workflowStore.isWorkItemCreationAllowed(projectId, stateId))
      );
    } else if (filterAvailableStateIds && issueId) {
      const allowedIds =
        workflowStore.getAllowedStateIdsForIssue(issueId) ??
        workflowStore.getAllowedTargetStatesForProject(projectId, currentStateId);
      if (allowedIds) allowedStateIds = new Set(currentStateId ? [...allowedIds, currentStateId] : allowedIds);
    }
  }

  return (
    <StateSelectBlock
      getValues={getValues}
      value={selected}
      onChange={onChange}
      variant={variant}
      disabled={disabled}
      placeholder={placeholder ?? t("state")}
      onClose={onClose}
      className={className}
      tooltip={resolvedTooltip}
      appendElement={appendElement}
      testId={testId}
      tabIndex={tabIndex}
      allowedStateIds={allowedStateIds}
    />
  );
});
