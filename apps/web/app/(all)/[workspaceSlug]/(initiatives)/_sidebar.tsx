/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { SIDEBAR_WIDTH } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
import { useTranslation } from "@plane/i18n";
import { InitiativesSidebarTree } from "@/components/initiatives/sidebar-tree";
import { ResizableSidebar } from "@/components/sidebar/resizable-sidebar";
import { SidebarWrapper } from "@/components/sidebar/sidebar-wrapper";
import { useAppTheme } from "@/hooks/store/use-app-theme";

/**
 * The contextual sidebar of the Initiatives app: the goals with their initiatives. It shares the
 * collapsed state, the peek and the width with the Projects sidebar, as one sidebar of the shell.
 */
export const InitiativesAppSidebar = observer(function InitiativesAppSidebar() {
  const { t } = useTranslation();
  const { sidebarCollapsed, toggleSidebar, sidebarPeek, toggleSidebarPeek, isAnySidebarDropdownOpen } = useAppTheme();
  const { storedValue, setValue } = useLocalStorage("sidebarWidth", SIDEBAR_WIDTH);
  const [sidebarWidth, setSidebarWidth] = useState<number>(storedValue ?? SIDEBAR_WIDTH);

  return (
    <ResizableSidebar
      showPeek={sidebarPeek}
      defaultWidth={storedValue ?? 250}
      width={sidebarWidth}
      setWidth={setSidebarWidth}
      defaultCollapsed={sidebarCollapsed}
      peekDuration={1500}
      onWidthChange={(width) => setValue(width)}
      onCollapsedChange={toggleSidebar}
      isCollapsed={sidebarCollapsed}
      toggleCollapsed={toggleSidebar}
      togglePeek={toggleSidebarPeek}
      isAnySidebarDropdownOpen={isAnySidebarDropdownOpen}
    >
      <SidebarWrapper title={t("initiatives.title")}>
        <InitiativesSidebarTree />
      </SidebarWrapper>
    </ResizableSidebar>
  );
});
