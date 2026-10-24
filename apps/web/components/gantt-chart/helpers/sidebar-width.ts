/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the resizable timeline sidebar of inomotech-foss/paperplane (AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { getValueFromLocalStorage } from "@/hooks/use-local-storage";
import {
  SIDEBAR_MAX_WIDTH,
  SIDEBAR_MIN_CHART_WIDTH,
  SIDEBAR_MIN_WIDTH,
  SIDEBAR_WIDTH,
  SIDEBAR_WIDTH_PROPERTY,
  SIDEBAR_WIDTH_STORAGE_KEY,
} from "../constants";

/** The widest the sidebar may be in a container of this width, so that the chart keeps its room. */
export const getSidebarMaxWidth = (containerWidth: number) =>
  Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, containerWidth - SIDEBAR_MIN_CHART_WIDTH));

/** A width inside the allowed range (the upper bound also depends on the container, when known). */
export const clampSidebarWidth = (width: number, containerWidth?: number) =>
  Math.round(
    Math.min(
      Math.max(width, SIDEBAR_MIN_WIDTH),
      containerWidth === undefined ? SIDEBAR_MAX_WIDTH : getSidebarMaxWidth(containerWidth)
    )
  );

/** The width saved by the user, or the default. */
export const getStoredSidebarWidth = (): number => {
  const stored = Number(getValueFromLocalStorage(SIDEBAR_WIDTH_STORAGE_KEY, SIDEBAR_WIDTH));
  return Number.isFinite(stored) ? clampSidebarWidth(stored) : SIDEBAR_WIDTH;
};

/** The sidebar width as it is laid out right now, also while it is being dragged. */
export const getSidebarWidth = (container: HTMLElement | null | undefined): number => {
  const live = Number.parseFloat(container?.style.getPropertyValue(SIDEBAR_WIDTH_PROPERTY) ?? "");
  return Number.isFinite(live) ? live : SIDEBAR_WIDTH;
};
