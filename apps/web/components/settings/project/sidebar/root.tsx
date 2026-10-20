/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import { ScrollArea } from "@makeplane/propel/components/scroll-area";
import { cn } from "@plane/utils";
// components
import { SettingsSidebarResizeHandle, useSettingsSidebarWidth } from "@/components/settings/sidebar-resize";
// local imports
import { ProjectSettingsSidebarHeader } from "./header";
import { ProjectSettingsSidebarItemCategories } from "./item-categories";

type Props = {
  projectId: string;
  className?: string;
  /** Show the drag handle and use the width the user chose. Off in the mobile menu. */
  resizable?: boolean;
};

export function ProjectSettingsSidebarRoot(props: Props) {
  const { projectId, className, resizable = false } = props;
  // hooks
  const { width, isResizing, startResizing, resetWidth } = useSettingsSidebarWidth();

  return (
    <div
      className={cn(
        "relative flex h-full shrink-0 animate-fade-in flex-col overflow-hidden border-r border-r-subtle bg-surface-1",
        !resizable && "w-[250px]",
        className
      )}
      style={resizable ? { width } : undefined}
    >
      <ScrollArea orientation="vertical">
        <div className="pb-5">
          <ProjectSettingsSidebarHeader projectId={projectId} />
          <ProjectSettingsSidebarItemCategories projectId={projectId} />
        </div>
      </ScrollArea>
      {resizable && (
        <SettingsSidebarResizeHandle isResizing={isResizing} onMouseDown={startResizing} onDoubleClick={resetWidth} />
      )}
    </div>
  );
}
