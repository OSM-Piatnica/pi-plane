/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
import { useWorkspaceIssueProperties } from "@/hooks/use-workspace-issue-properties";
// local imports
import { AllIssueQuickActions } from "../../quick-action-dropdowns";
import { BaseListRoot } from "../base-list-root";

type Props = {
  workspaceSlug: string;
  globalViewId: string;
};

/** The list (and its groups) of a workspace view such as "Assigned" or "Created" in My work items. */
export const WorkspaceListLayout = observer(function WorkspaceListLayout(props: Props) {
  const { workspaceSlug, globalViewId } = props;
  // the projects, labels and states the list shows by name
  useWorkspaceIssueProperties(workspaceSlug);
  // store
  const { allowPermissions } = useUserPermissions();

  const canEditPropertiesBasedOnProject = (projectId: string) =>
    allowPermissions(
      [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
      EUserPermissionsLevel.PROJECT,
      workspaceSlug,
      projectId
    );

  return (
    <BaseListRoot
      QuickActions={AllIssueQuickActions}
      canEditPropertiesBasedOnProject={canEditPropertiesBasedOnProject}
      viewId={globalViewId}
    />
  );
});
