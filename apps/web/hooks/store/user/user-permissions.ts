/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// mobx store
import { StoreContext } from "@/lib/store-context";
import type { IUserPermissionStore } from "@/store/user/permission.store";

export const useUserPermissions = (): IUserPermissionStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useUserPermissions must be used within StoreProvider");

  return context.user.permission;
};
