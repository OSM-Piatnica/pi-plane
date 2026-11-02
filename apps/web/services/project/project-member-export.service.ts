/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TProjectMemberExportParams } from "@plane/types";
import { filenameFromContentDisposition } from "@/helpers/project-member-export";
import { APIService } from "@/services/api.service";

/** Downloads the members of a project as a file. */
export class ProjectMemberExportService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async download(
    workspaceSlug: string,
    projectId: string,
    params: TProjectMemberExportParams
  ): Promise<{ blob: Blob; filename: string }> {
    return this.get(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/members/export/`,
      { params },
      { responseType: "blob" }
    )
      .then((response) => ({
        blob: response.data as Blob,
        filename: filenameFromContentDisposition(
          response.headers?.["content-disposition"],
          `project-members.${params.format}`
        ),
      }))
      .catch(async (error) => {
        // an error answer is JSON, but arrives as a blob here
        let body = error?.response?.data;
        if (body instanceof Blob)
          body = await body
            .text()
            .then((text) => JSON.parse(text))
            .catch(() => undefined);
        throw body;
      });
  }
}

export const projectMemberExportService = new ProjectMemberExportService();
