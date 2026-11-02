/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TProjectMemberImportRow, TProjectMemberImportSummary } from "@plane/types";
import { APIService } from "@/services/api.service";

/** Adds the people and groups of a CSV file to a project. */
export class ProjectMemberImportService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async importRows(
    workspaceSlug: string,
    projectId: string,
    rows: TProjectMemberImportRow[]
  ): Promise<TProjectMemberImportSummary> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/members/import/`, { rows })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

export const projectMemberImportService = new ProjectMemberImportService();
