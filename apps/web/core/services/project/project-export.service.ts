/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TWorkItemFilterExpression } from "@plane/types";
import { buildProjectExportRequestBody } from "@/helpers/export-payload-helpers";
import { APIService } from "@/services/api.service";
// helpers

export class ProjectExportService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async csvExport(
    workspaceSlug: string,
    data: {
      provider: string;
      project: string[];
      multiple?: boolean;
      delimiter?: "," | ";";
      rich_filters?: TWorkItemFilterExpression;
    }
  ): Promise<any> {
    return this.post(`/api/workspaces/${workspaceSlug}/export-issues/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async exportProject(
    workspaceSlug: string,
    projectIds: string[],
    options: { provider: string; delimiter?: "," | ";" }
  ): Promise<Blob> {
    return this.post(
      `/api/workspaces/${workspaceSlug}/export-projects/`,
      buildProjectExportRequestBody(projectIds, options),
      { responseType: "blob" }
    )
      .then((response) => response?.data as Blob)
      .catch(async (error) => {
        if (error?.response?.data instanceof Blob) {
          const text = await error.response.data.text();
          try {
            throw JSON.parse(text);
          } catch {
            throw { error: text };
          }
        }
        throw error?.response?.data;
      });
  }

  async getProjectExportHistory(workspaceSlug: string, cursor: string, perPage: number) {
    return this.get(`/api/workspaces/${workspaceSlug}/export-projects/`, {
      params: { per_page: perPage, cursor },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
