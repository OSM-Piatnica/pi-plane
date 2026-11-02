/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { UserGroupsSettings } from "@/components/workspace/user-groups/user-groups-settings";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import type { Route } from "./+types/page";
import { GroupsWorkspaceSettingsHeader } from "./header";

const WorkspaceGroupsSettingsPage = observer(function WorkspaceGroupsSettingsPage({ params }: Route.ComponentProps) {
  // router
  const { workspaceSlug } = params;
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentWorkspace } = useWorkspace();
  // derived values
  const canViewGroups = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace.name} - Groups` : undefined;

  if (workspaceUserInfo && !canViewGroups) {
    return <NotAuthorizedView section="settings" className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<GroupsWorkspaceSettingsHeader />}>
      <PageHead title={pageTitle} />
      <UserGroupsSettings workspaceSlug={workspaceSlug} />
    </SettingsContentWrapper>
  );
});

export default WorkspaceGroupsSettingsPage;
