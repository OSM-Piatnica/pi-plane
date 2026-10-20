/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// mobx store
import { StoreContext } from "@/lib/store-context";
// types
import type { IPowerKStore } from "@/store/power-k.store";

export const usePowerK = (): IPowerKStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("usePowerK must be used within StoreProvider");
  return context.powerK;
};
