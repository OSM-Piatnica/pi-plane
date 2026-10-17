/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { IProjectIssues } from "@/store/issue/project";
import { ProjectIssues } from "@/store/issue/project";
import type { IIssueRootStore } from "@/store/issue/root.store";
import type { IProjectEpicsFilter } from "./filter.store";

// @ts-nocheck - This class will never be used, extending similar class to avoid type errors

export type IProjectEpics = IProjectIssues;

// @ts-nocheck - This class will never be used, extending similar class to avoid type errors
export class ProjectEpics extends ProjectIssues implements IProjectEpics {
  // oxlint-disable-next-line no-useless-constructor -- deliberate extension-point constructor kept for subclass/override parity
  constructor(_rootStore: IIssueRootStore, issueFilterStore: IProjectEpicsFilter) {
    super(_rootStore, issueFilterStore);
  }
}
