import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";
import type { TProjectCsvImportResult } from "@/helpers/project-csv-helpers";

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
