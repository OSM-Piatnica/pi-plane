/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EIssueServiceType } from "@plane/types";
import { resolveWeekendDays } from "@/helpers/weekend-days";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserProfile } from "@/hooks/store/user";

/**
 * The non-working days of one project, for work item pages that have no project in their address (a work item
 * opened by its key, its peek view, the create modal). Until the project has loaded, the workspace's days stand in
 * for it, never the person's own: a duration has to be counted with the project's days or not at all.
 */
export const useProjectWeekendDays = (projectId: string | null | undefined): number[] => {
  const { data: userProfile } = useUserProfile();
  const { getProjectById } = useProject();
  const { currentWorkspace, workspaces } = useWorkspace();
  const workspace =
    currentWorkspace ?? (userProfile?.last_workspace_id ? workspaces[userProfile.last_workspace_id] : undefined);

  return resolveWeekendDays({
    project: projectId ? (getProjectById(projectId) ?? {}) : undefined,
    workspace: workspace?.weekend_days,
  });
};

/**
 * The same, for many work items at once: a function that gives the weekend days of the project a work item is in,
 * for the timeline's dependency arrows, which compare dates of work items from several projects.
 */
export const useGetIssueWeekendDays = (): ((issueId: string) => number[]) => {
  const { data: userProfile } = useUserProfile();
  const { getProjectById } = useProject();
  const { currentWorkspace, workspaces } = useWorkspace();
  const {
    issue: { getIssueById },
  } = useIssueDetail(EIssueServiceType.ISSUES);
  const workspace =
    currentWorkspace ?? (userProfile?.last_workspace_id ? workspaces[userProfile.last_workspace_id] : undefined);

  return (issueId: string) => {
    const projectId = getIssueById(issueId)?.project_id;
    return resolveWeekendDays({
      project: projectId ? (getProjectById(projectId) ?? {}) : undefined,
      workspace: workspace?.weekend_days,
    });
  };
};
