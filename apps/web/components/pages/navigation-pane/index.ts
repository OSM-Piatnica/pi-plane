/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export * from "./root";
export * from "./types";

export type TPageNavigationPaneTab = "outline" | "info" | "assets";

export const PAGE_NAVIGATION_PANE_TABS_LIST: Record<
  TPageNavigationPaneTab,
  {
    key: TPageNavigationPaneTab;
    i18n_label: string;
  }
> = {
  outline: {
    key: "outline",
    i18n_label: "page_navigation_pane.tabs.outline.label",
  },
  info: {
    key: "info",
    i18n_label: "page_navigation_pane.tabs.info.label",
  },
  assets: {
    key: "assets",
    i18n_label: "page_navigation_pane.tabs.assets.label",
  },
};

export const ORDERED_PAGE_NAVIGATION_TABS_LIST: {
  key: TPageNavigationPaneTab;
  i18n_label: string;
}[] = [
  PAGE_NAVIGATION_PANE_TABS_LIST.outline,
  PAGE_NAVIGATION_PANE_TABS_LIST.info,
  PAGE_NAVIGATION_PANE_TABS_LIST.assets,
];

export const PAGE_NAVIGATION_PANE_WIDTH = 294;

export const PAGE_NAVIGATION_PANE_TABS_QUERY_PARAM = "paneTab";
export const PAGE_NAVIGATION_PANE_VERSION_QUERY_PARAM = "version";

export const PAGE_NAVIGATION_PANE_TAB_KEYS = ORDERED_PAGE_NAVIGATION_TABS_LIST.map((tab) => tab.key);
