/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { resolveWeekendDays } from "@/helpers/weekend-days";
import { useProject } from "@/hooks/store/use-project";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserProfile } from "@/hooks/store/user";

/** The non-working days for the page being viewed: the project's inside a project, else the person's or the workspace's. */
export const useWeekendDays = (): number[] => {
  const { data: userProfile } = useUserProfile();
  const { currentProjectDetails } = useProject();
  const { currentWorkspace, workspaces } = useWorkspace();
  // Pages outside a workspace (profile settings) take the workspace the person last opened
  const workspace =
    currentWorkspace ?? (userProfile?.last_workspace_id ? workspaces[userProfile.last_workspace_id] : undefined);

  return resolveWeekendDays({
    profile: userProfile?.weekend_days,
    project: currentProjectDetails,
    workspace: workspace?.weekend_days,
  });
};
