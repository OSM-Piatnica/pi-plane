/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { EProjectGroupRole, TAssignableGroup, TProjectGroup, TProjectGroupFormData } from "@plane/types";
import { APIService } from "@/services/api.service";

/** The groups that are members of a project. */
export class ProjectGroupService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(workspaceSlug: string, projectId: string): Promise<TProjectGroup[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/groups/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** The groups work items of the project can be assigned to: the project's groups and the ones below them. */
  async listAssignable(workspaceSlug: string, projectId: string): Promise<TAssignableGroup[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/groups/`, { params: { assignable: 1 } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async add(workspaceSlug: string, projectId: string, data: TProjectGroupFormData): Promise<TProjectGroup> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/groups/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateRole(
    workspaceSlug: string,
    projectId: string,
    linkId: string,
    role: EProjectGroupRole
  ): Promise<TProjectGroup> {
    return this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/groups/${linkId}/`, { role })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, projectId: string, linkId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/projects/${projectId}/groups/${linkId}/`)
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

export const projectGroupService = new ProjectGroupService();
