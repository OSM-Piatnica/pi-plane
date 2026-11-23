/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// lib
import { StoreContext } from "@/lib/store-context";
import type { IScheduleAnalysisStore } from "@/store/schedule-analysis.store";

/** The schedule analysis (critical path and float) shared by the timeline, the list layouts and the sidebar. */
export const useScheduleAnalysis = (): IScheduleAnalysisStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useScheduleAnalysis must be used within StoreProvider");
  return context.scheduleAnalysis;
};
