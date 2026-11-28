/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  TDocumentLibraries,
  TDocumentLibrary,
  TDocumentLibraryCreate,
  TDocumentLibraryUpdate,
  TDocumentSite,
  TProjectDocumentFolder,
  TProjectDocumentSettings,
  TProjectDocumentSettingsUpdate,
} from "@plane/types";
import { APIService } from "@/services/api.service";

/** Document libraries of a workspace and a project's choice of library and folder (docs/document-libraries.md). */
export class DocumentLibraryService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private libraries(workspaceSlug: string) {
    return `/api/workspaces/${workspaceSlug}/document-libraries/`;
  }

  private projectSettings(workspaceSlug: string, projectId: string) {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/document-settings/`;
  }

  async list(workspaceSlug: string): Promise<TDocumentLibraries> {
    return this.get(this.libraries(workspaceSlug))
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Looks the site up through Microsoft Graph and lists its document libraries. */
  async lookUpSite(workspaceSlug: string, siteUrl: string): Promise<TDocumentSite> {
    return this.post(`${this.libraries(workspaceSlug)}sites/`, { site_url: siteUrl })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(workspaceSlug: string, data: TDocumentLibraryCreate): Promise<TDocumentLibrary> {
    return this.post(this.libraries(workspaceSlug), data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(workspaceSlug: string, libraryId: string, data: TDocumentLibraryUpdate): Promise<TDocumentLibrary> {
    return this.patch(`${this.libraries(workspaceSlug)}${libraryId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, libraryId: string): Promise<void> {
    return this.delete(`${this.libraries(workspaceSlug)}${libraryId}/`)
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** The default library of the workspace; `null` makes Pi-Plane storage the default. */
  async setDefault(workspaceSlug: string, libraryId: string | null): Promise<void> {
    return this.post(`${this.libraries(workspaceSlug)}default/`, { library_id: libraryId })
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjectSettings(workspaceSlug: string, projectId: string): Promise<TProjectDocumentSettings> {
    return this.get(this.projectSettings(workspaceSlug, projectId))
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateProjectSettings(
    workspaceSlug: string,
    projectId: string,
    data: TProjectDocumentSettingsUpdate
  ): Promise<TProjectDocumentSettings> {
    return this.put(this.projectSettings(workspaceSlug, projectId), data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Asks SharePoint for the project's folder; until the first upload it does not exist. */
  async getProjectFolder(workspaceSlug: string, projectId: string): Promise<TProjectDocumentFolder> {
    return this.get(`${this.projectSettings(workspaceSlug, projectId)}folder/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

export const documentLibraryService = new DocumentLibraryService();
