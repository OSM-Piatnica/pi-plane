/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { IProjectViewIssuesFilter } from "@/store/issue/project-views";
import { ProjectViewIssuesFilter } from "@/store/issue/project-views";
import type { IIssueRootStore } from "@/store/issue/root.store";

// @ts-nocheck - This class will never be used, extending similar class to avoid type errors
export type ITeamViewIssuesFilter = IProjectViewIssuesFilter;

// @ts-nocheck - This class will never be used, extending similar class to avoid type errors
export class TeamViewIssuesFilter extends ProjectViewIssuesFilter implements IProjectViewIssuesFilter {
  // oxlint-disable-next-line no-useless-constructor -- deliberate extension-point constructor kept for subclass/override parity
  constructor(_rootStore: IIssueRootStore) {
    super(_rootStore);
  }
}
