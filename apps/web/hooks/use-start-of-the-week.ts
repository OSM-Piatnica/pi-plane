/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { EStartOfTheWeek } from "@plane/types";
import { resolveStartOfTheWeek } from "@/helpers/start-of-the-week";
import { useProject } from "@/hooks/store/use-project";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserProfile } from "@/hooks/store/user";

/** The first day of the week for the page being viewed: the person's own choice, else the project's, else the workspace's. */
export const useStartOfTheWeek = (): EStartOfTheWeek => {
  const { data: userProfile } = useUserProfile();
  const { currentProjectDetails } = useProject();
  const { currentWorkspace, workspaces } = useWorkspace();
  // Pages outside a workspace (profile settings) take the workspace the person last opened
  const workspace =
    currentWorkspace ?? (userProfile?.last_workspace_id ? workspaces[userProfile.last_workspace_id] : undefined);

  return resolveStartOfTheWeek({
    profile: userProfile?.start_of_the_week,
    project: currentProjectDetails?.start_of_the_week,
    workspace: workspace?.start_of_the_week,
  });
};
