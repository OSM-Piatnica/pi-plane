/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Outlet } from "react-router";
import useSWR from "swr";
import { AppRailAppGuard } from "@/components/app-rail/app-guard";
import { AppRailAppSidebar } from "@/components/app-rail/app-sidebar";
import { ProjectsAppPowerKProvider } from "@/components/power-k/projects-app-provider";
import { useInitiative } from "@/hooks/store/use-initiative";

/** Loads the initiatives of the workspace once for the sidebar tree, the list and the detail pages */
const InitiativesLoader = observer(function InitiativesLoader() {
  const { workspaceSlug } = useParams();
  const { fetchInitiatives } = useInitiative();
  const slug = workspaceSlug?.toString();
  useSWR(slug ? `WORKSPACE_INITIATIVES_${slug}` : null, slug ? () => fetchInitiatives(slug) : null, {
    revalidateOnFocus: false,
  });
  return null;
});

/** The Initiatives app: goals and initiatives across projects (`docs/initiatives.md`) */
export default function InitiativesLayout() {
  return (
    <AppRailAppGuard appKey="initiatives">
      <ProjectsAppPowerKProvider />
      <InitiativesLoader />
      <div className="relative flex h-full w-full flex-col overflow-hidden rounded-lg border border-subtle">
        <div className="relative flex size-full overflow-hidden">
          <AppRailAppSidebar appKey="initiatives" />
          <main className="relative flex h-full w-full flex-col overflow-hidden bg-surface-1">
            <Outlet />
          </main>
        </div>
      </div>
    </AppRailAppGuard>
  );
}
