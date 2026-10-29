/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import { TabsPanel } from "@makeplane/propel/components/tabs";
// components
import type { TPageRootHandlers } from "@/components/pages/editor/page-root";
import { ORDERED_PAGE_NAVIGATION_TABS_LIST } from "@/components/pages/navigation-pane";
// store
import type { TPageInstance } from "@/store/pages/base-page";
// local imports
import { PageNavigationPaneAssetsTabPanel } from "./assets";
import { PageNavigationPaneInfoTabPanel } from "./info/root";
import { PageNavigationPaneOutlineTabPanel } from "./outline";
import type { TPageNavigationPaneTab } from "..";

type Props = {
  page: TPageInstance;
  versionHistory: Pick<TPageRootHandlers, "fetchAllVersions" | "fetchVersionDetails">;
};

export function PageNavigationPaneTabPanelsRoot(props: Props) {
  const { page, versionHistory } = props;

  return (
    // Grid wrapper: Propel's TabsPanel omits className, so the single mounted panel gets its
    // fill height from a one-row grid instead.
    <div className="grid min-h-0 w-full flex-1 grid-rows-1 overflow-hidden py-2">
      {ORDERED_PAGE_NAVIGATION_TABS_LIST.map((tab) => (
        <TabsPanel key={tab.key} value={tab.key}>
          {tab.key === "outline" && <PageNavigationPaneOutlineTabPanel page={page} />}
          {tab.key === "info" && <PageNavigationPaneInfoTabPanel page={page} versionHistory={versionHistory} />}
          {tab.key === "assets" && <PageNavigationPaneAssetsTabPanel page={page} />}
          <PageNavigationPaneAdditionalTabPanelsRoot activeTab={tab.key} page={page} />
        </TabsPanel>
      ))}
    </div>
  );
}

// store
// local imports

export type TPageNavigationPaneAdditionalTabPanelsRootProps = {
  activeTab: TPageNavigationPaneTab;
  page: TPageInstance;
};

export function PageNavigationPaneAdditionalTabPanelsRoot(_props: TPageNavigationPaneAdditionalTabPanelsRootProps) {
  return null;
}
