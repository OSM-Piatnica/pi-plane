/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
import type { TBaselineVariance, TBaselineVarianceScope, TProjectBaseline, TProjectBaselineList } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export type TProjectBaselineUpdate = Partial<Pick<TProjectBaseline, "name" | "description" | "is_active">>;

/** Baselines of a project: saved plans the timeline compares the current dates with. */
export class ProjectBaselineService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private url(workspaceSlug: string, projectId: string): string {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/baselines/`;
  }

  async list(workspaceSlug: string, projectId: string): Promise<TProjectBaselineList> {
    return this.get(this.url(workspaceSlug, projectId))
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Save the current plan of the project as a new baseline; it becomes the active one. */
  async create(
    workspaceSlug: string,
    projectId: string,
    data: { name: string; description?: string }
  ): Promise<TProjectBaseline> {
    return this.post(this.url(workspaceSlug, projectId), data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(
    workspaceSlug: string,
    projectId: string,
    baselineId: string,
    data: TProjectBaselineUpdate
  ): Promise<TProjectBaseline> {
    return this.patch(`${this.url(workspaceSlug, projectId)}${baselineId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, projectId: string, baselineId: string): Promise<void> {
    return this.delete(`${this.url(workspaceSlug, projectId)}${baselineId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** The current dates against the active baseline, or the one named in the scope. */
  async getVariance(
    workspaceSlug: string,
    projectId: string,
    scope: TBaselineVarianceScope = {}
  ): Promise<TBaselineVariance> {
    return this.get(`${this.url(workspaceSlug, projectId)}variance/`, { params: scope })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
