/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export const BLOCK_HEIGHT = 44;

export const HEADER_HEIGHT = 48;

export const GANTT_BREADCRUMBS_HEIGHT = 40;

export const SIDEBAR_WIDTH = 360;

export const SIDEBAR_MIN_WIDTH = 240;

export const SIDEBAR_MAX_WIDTH = 720;

/** The room the chart keeps next to the sidebar. */
export const SIDEBAR_MIN_CHART_WIDTH = 240;

export const SIDEBAR_WIDTH_STORAGE_KEY = "timeline_sidebar_width";

/**
 * The live width of the sidebar, a CSS property of #gantt-container. Dragging the handle sets it directly, so the rows
 * are laid out by the browser and do not render on every mouse move; the width is committed to the store on release.
 */
export const SIDEBAR_WIDTH_PROPERTY = "--timeline-sidebar-width";

/** What layout reads: the live sidebar width. */
export const SIDEBAR_WIDTH_VAR = `var(${SIDEBAR_WIDTH_PROPERTY}, ${SIDEBAR_WIDTH}px)`;

export const DEFAULT_BLOCK_WIDTH = 60;

export const GANTT_SELECT_GROUP = "gantt-issues";
