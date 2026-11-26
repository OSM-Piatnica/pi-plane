/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Outlet } from "react-router";
import { AppRailAppSidebar } from "@/components/app-rail/app-sidebar";
import { ModuleSubIssuesConfirmModal } from "@/components/issues/module-sub-issues-confirm-modal";
import { ProjectsAppPowerKProvider } from "@/components/power-k/projects-app-provider";
import { StickyActionBar } from "@/components/stickies/action-bar";
import { DuplicateCancelConfirmModal } from "@/components/workflow/duplicate-cancel-confirm-modal";
import { ParentReopenConfirmModal } from "@/components/workflow/parent-reopen-confirm-modal";
import { RescheduleConfirmModal } from "@/components/workflow/reschedule-confirm-modal";
import { ExtendedProjectSidebar } from "./extended-project-sidebar";

function WorkspaceLayout() {
  return (
    <>
      <ProjectsAppPowerKProvider />
      <ParentReopenConfirmModal />
      <ModuleSubIssuesConfirmModal />
      <DuplicateCancelConfirmModal />
      <RescheduleConfirmModal />
      <div className="relative flex h-full w-full flex-col overflow-hidden rounded-lg border border-subtle">
        <div id="full-screen-portal" className="absolute inset-0 w-full" />
        <div className="relative flex size-full overflow-hidden">
          <AppRailAppSidebar appKey="projects" />
          <ExtendedProjectSidebar />
          <main className="relative flex h-full w-full flex-col overflow-hidden bg-surface-1">
            <Outlet />
          </main>
        </div>
        <div className="absolute bottom-0.5 left-3 z-20">
          <StickyActionBar />
        </div>
      </div>
    </>
  );
}

export default observer(WorkspaceLayout);
