/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the resizable timeline sidebar of inomotech-foss/paperplane (AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// hooks
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";
// local imports
import { SIDEBAR_MIN_WIDTH, SIDEBAR_WIDTH, SIDEBAR_WIDTH_PROPERTY } from "../constants";
import { clampSidebarWidth, getSidebarMaxWidth } from "../helpers/sidebar-width";

const KEY_STEP = 16;
const KEY_STEP_LARGE = 64;

/** The handle on the right edge of the timeline sidebar: drag it, or use the arrow keys, to change the width. */
export const TimelineSidebarResizeHandle = observer(function TimelineSidebarResizeHandle() {
  const { t } = useTranslation();
  const { sidebarWidth, setSidebarWidth } = useTimeLineChartStore();
  const handleRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ startX: number; startWidth: number; width: number } | null>(null);
  const [isResizing, setIsResizing] = useState(false);

  const getContainer = () => handleRef.current?.closest<HTMLElement>("#gantt-container") ?? null;

  // shows a width without rendering the rows: the browser lays them out from the CSS property
  const preview = (width: number) => {
    getContainer()?.style.setProperty(SIDEBAR_WIDTH_PROPERTY, `${width}px`);
    handleRef.current?.setAttribute("aria-valuenow", `${width}`);
  };

  // a narrower container (window resize, full screen) takes room from the sidebar, but does not change the saved width
  useEffect(() => {
    const container = getContainer();
    if (!container || typeof ResizeObserver === "undefined") return;
    const resizeObserver = new ResizeObserver(() => {
      const max = getSidebarMaxWidth(container.clientWidth);
      if (sidebarWidth > max) setSidebarWidth(max, false);
    });
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [sidebarWidth, setSidebarWidth]);

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { startX: event.clientX, startWidth: sidebarWidth, width: sidebarWidth };
    setIsResizing(true);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    drag.width = clampSidebarWidth(drag.startWidth + event.clientX - drag.startX, getContainer()?.clientWidth);
    preview(drag.width);
  };

  const handlePointerEnd = () => {
    const drag = dragRef.current;
    dragRef.current = null;
    setIsResizing(false);
    if (drag) setSidebarWidth(drag.width);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const containerWidth = getContainer()?.clientWidth;
    const step = event.shiftKey ? KEY_STEP_LARGE : KEY_STEP;
    const next =
      event.key === "ArrowLeft"
        ? sidebarWidth - step
        : event.key === "ArrowRight"
          ? sidebarWidth + step
          : event.key === "Home"
            ? SIDEBAR_MIN_WIDTH
            : event.key === "End"
              ? Number.POSITIVE_INFINITY
              : undefined;
    if (next === undefined) return;
    event.preventDefault();
    setSidebarWidth(clampSidebarWidth(next, containerWidth));
  };

  return (
    <div
      ref={handleRef}
      // A focusable separator is a widget, which an hr cannot be.
      // oxlint-disable-next-line jsx_a11y/prefer-tag-over-role
      role="separator"
      aria-orientation="vertical"
      aria-controls="gantt-sidebar"
      aria-valuemin={SIDEBAR_MIN_WIDTH}
      aria-valuemax={clampSidebarWidth(Number.POSITIVE_INFINITY, getContainer()?.clientWidth)}
      aria-valuenow={sidebarWidth}
      aria-label={t("core_ui.sidebar.resize")}
      tabIndex={0}
      className={cn(
        "absolute top-0 right-0 z-[20] h-full w-1 translate-x-1/2 cursor-ew-resize touch-none outline-none",
        "transition-colors duration-200 hover:bg-surface-2 focus-visible:w-1.5 focus-visible:bg-accent-primary",
        // a wider transparent hit area around the 4px line
        "after:absolute after:inset-y-0 after:-right-1.5 after:-left-1.5 after:content-['']",
        isResizing && "w-1.5 bg-layer-1"
      )}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onKeyDown={handleKeyDown}
      onDoubleClick={() => setSidebarWidth(SIDEBAR_WIDTH)}
    />
  );
});
