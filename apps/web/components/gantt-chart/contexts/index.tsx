/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { createContext, useContext } from "react";
import type { TTimelineType } from "@plane/types";

export const TimeLineTypeContext = createContext<TTimelineType | undefined>(undefined);

export const useTimeLineType = () => {
  const timelineType = useContext(TimeLineTypeContext);
  return timelineType;
};

/** Sub-work items shown under their parent in the issue timeline (see `BaseGanttRoot`). */
export type TGanttSubWorkItems = {
  /** Indentation level per row id; rows that are not listed are top-level. */
  levelById: Record<string, number>;
  expandedIds: ReadonlySet<string>;
  loadingIds: ReadonlySet<string>;
  toggle: (workItemId: string) => void;
};

/** `undefined` where the timeline does not expand sub-work items (cycles, modules of the modules timeline, ...). */
export const GanttSubWorkItemsContext = createContext<TGanttSubWorkItems | undefined>(undefined);

export const useGanttSubWorkItems = () => useContext(GanttSubWorkItemsContext);
