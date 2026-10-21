/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
// hooks
import { canGoBackInHistory } from "@/helpers/home-navigation.helper";
import { useAppRouter } from "@/hooks/use-app-router";

/**
 * Returns a handler that goes back in history, or to the root route when the page was opened
 * directly (new tab, shared link) and there is no previous entry to return to.
 */
export const useGoBackOrHome = () => {
  const router = useAppRouter();

  return useCallback(() => {
    if (canGoBackInHistory(window.history.length)) router.back();
    else router.push("/");
  }, [router]);
};
