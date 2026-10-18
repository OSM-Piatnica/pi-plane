/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { BoardOutline, ListOutline, TimelineOutline } from "@makeplane/propel/icons";
import type { IBaseLayoutConfig } from "@plane/types";

export const BASE_LAYOUTS: IBaseLayoutConfig[] = [
  {
    key: "list",
    icon: ListOutline,
    label: "issue.layouts.title.list",
  },
  {
    key: "kanban",
    icon: BoardOutline,
    label: "issue.layouts.title.kanban",
  },
  {
    key: "gantt",
    icon: TimelineOutline,
    label: "app_text.base_layouts.gantt",
  },
];
