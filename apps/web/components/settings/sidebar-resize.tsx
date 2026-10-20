/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { MouseEvent as ReactMouseEvent } from "react";
// plane imports
import { SIDEBAR_WIDTH } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// hooks
import { useResizableWidth } from "@/hooks/use-resizable-width";

/** Width of the settings sidebars (workspace and project settings share it). Double-click the handle to reset. */
export const useSettingsSidebarWidth = () =>
  useResizableWidth({ storageKey: "settingsSidebarWidth", defaultWidth: SIDEBAR_WIDTH, minWidth: 236, maxWidth: 350 });

type TSettingsSidebarResizeHandleProps = {
  isResizing: boolean;
  onMouseDown: (event: ReactMouseEvent) => void;
  onDoubleClick: () => void;
};

export function SettingsSidebarResizeHandle(props: TSettingsSidebarResizeHandleProps) {
  const { isResizing, onMouseDown, onDoubleClick } = props;
  // plane hooks
  const { t } = useTranslation();

  return (
    // react-doctor-disable-next-line interactive-supports-focus -- mouse-only drag handle; resizing has no keyboard equivalent here
    <div // oxlint-disable-line jsx-a11y/interactive-supports-focus -- mouse-only drag handle
      className={cn(
        "absolute top-0 right-0 z-[20] h-full w-1 cursor-ew-resize transition-all duration-200",
        isResizing ? "w-1.5 bg-layer-1" : "hover:bg-surface-2"
      )}
      onMouseDown={onMouseDown}
      onDoubleClick={onDoubleClick}
      role="separator"
      aria-orientation="vertical"
      aria-label={t("core_ui.sidebar.resize")}
    />
  );
}
