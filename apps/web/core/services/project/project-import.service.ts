/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026 Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";
import type { TProjectCsvImportResult } from "@/helpers/project-csv-helpers";

export type TWorkItemImportResult = {
  message: string;
  project_id: string;
  project_identifier: string;
  project_name: string;
  created_work_items: number;
  warnings: string[];
  history_id: string;
};

export class ProjectImportService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async importProjectCsv(workspaceSlug: string, file: File): Promise<TProjectCsvImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("provider", "csv");

    return this.post(`/api/workspaces/${workspaceSlug}/import-projects/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async importWorkItems(workspaceSlug: string, projectId: string, file: File): Promise<TWorkItemImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_id", projectId);
    const lower = file.name.toLowerCase();
    const provider = lower.endsWith(".json") ? "json" : lower.endsWith(".xlsx") ? "xlsx" : "csv";
    formData.append("provider", provider);

    return this.post(`/api/workspaces/${workspaceSlug}/import-work-items/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getImportHistory(workspaceSlug: string, cursor: string, perPage: number) {
    return this.get(`/api/workspaces/${workspaceSlug}/import-projects/`, {
      params: { per_page: perPage, cursor },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
