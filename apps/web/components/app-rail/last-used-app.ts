/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { APP_RAIL_LAST_USED_APP_STORAGE_KEY_PREFIX } from "@plane/constants";

type TStorage = Pick<Storage, "getItem" | "setItem">;

// reading `window.localStorage` itself throws when the browser blocks storage
const getBrowserStorage = (): TStorage | undefined => {
  try {
    return typeof window === "undefined" ? undefined : window.localStorage;
  } catch {
    return undefined;
  }
};

export const getLastUsedAppStorageKey = (workspaceSlug: string): string =>
  `${APP_RAIL_LAST_USED_APP_STORAGE_KEY_PREFIX}${workspaceSlug}`;

/**
 * The rail app last used in the workspace on this device, or undefined. It is a convenience kept
 * in `localStorage`: a blocked or full storage simply means nothing is remembered.
 */
export const readLastUsedApp = (
  workspaceSlug: string,
  storage: TStorage | undefined = getBrowserStorage()
): string | undefined => {
  try {
    return storage?.getItem(getLastUsedAppStorageKey(workspaceSlug)) || undefined;
  } catch {
    return undefined;
  }
};

export const writeLastUsedApp = (
  workspaceSlug: string,
  appKey: string,
  storage: TStorage | undefined = getBrowserStorage()
): void => {
  try {
    storage?.setItem(getLastUsedAppStorageKey(workspaceSlug), appKey);
  } catch {
    // nothing to do: the app is just not remembered
  }
};
