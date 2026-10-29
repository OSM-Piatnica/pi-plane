/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

export type TPageFlagHookArgs = {
  workspaceSlug: string;
};

export type TPageFlagHookReturnType = {
  isMovePageEnabled: boolean;
  isPageSharingEnabled: boolean;
};

export const usePageFlag = (args: TPageFlagHookArgs): TPageFlagHookReturnType => {
  // oxlint-disable-next-line no-empty-pattern -- extension-point stub; props intentionally unused in CE
  const {} = args;
  return {
    isMovePageEnabled: false,
    isPageSharingEnabled: false,
  };
};
