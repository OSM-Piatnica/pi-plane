/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { MouseEvent as ReactMouseEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
// plane imports
import { useLocalStorage } from "@plane/hooks";

type TOptions = {
  storageKey: string;
  defaultWidth: number;
  minWidth: number;
  maxWidth: number;
};

/**
 * Width of a panel that the user resizes by dragging its right edge. The width is kept in local storage
 * and written once the drag ends, not on every mouse move.
 */
export const useResizableWidth = ({ storageKey, defaultWidth, minWidth, maxWidth }: TOptions) => {
  // hooks
  const { storedValue, setValue } = useLocalStorage(storageKey, defaultWidth);
  // helpers
  const clamp = useCallback((value: number) => Math.min(Math.max(value, minWidth), maxWidth), [minWidth, maxWidth]);
  // states
  const [width, setWidth] = useState<number>(() => clamp(storedValue ?? defaultWidth));
  const [isResizing, setIsResizing] = useState(false);
  // refs
  const dragStartRef = useRef({ mouseX: 0, width: 0 });

  const startResizing = useCallback(
    (event: ReactMouseEvent) => {
      event.preventDefault();
      dragStartRef.current = { mouseX: event.clientX, width };
      setIsResizing(true);
    },
    [width]
  );

  const resetWidth = useCallback(() => {
    setWidth(defaultWidth);
    setValue(defaultWidth);
  }, [defaultWidth, setValue]);

  useEffect(() => {
    if (!isResizing) return;

    const widthAt = (event: MouseEvent) =>
      clamp(dragStartRef.current.width + event.clientX - dragStartRef.current.mouseX);
    const handleMouseMove = (event: MouseEvent) => setWidth(widthAt(event));
    const handleMouseUp = (event: MouseEvent) => {
      const finalWidth = widthAt(event);
      setWidth(finalWidth);
      setValue(finalWidth);
      setIsResizing(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, clamp, setValue]);

  return { width, isResizing, startResizing, resetWidth };
};
