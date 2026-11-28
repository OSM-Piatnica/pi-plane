/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  TInitiative,
  TInitiativeEpic,
  TInitiativeEpicOption,
  TInitiativeFormData,
  TInitiativeHealth,
  TInitiativeUpdate,
} from "@plane/types";
import { APIService } from "@/services/api.service";

/** Initiatives and goals of a workspace (`docs/initiatives.md`) */
export class InitiativeService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private url(workspaceSlug: string, suffix = "") {
    return `/api/workspaces/${workspaceSlug}/initiatives/${suffix}`;
  }

  private async unwrap<T>(call: Promise<{ data: T }>): Promise<T> {
    try {
      const response = await call;
      return response?.data;
    } catch (error) {
      throw (error as { response?: { data?: unknown } })?.response?.data;
    }
  }

  async list(workspaceSlug: string): Promise<TInitiative[]> {
    return this.unwrap(this.get(this.url(workspaceSlug)));
  }

  async retrieve(workspaceSlug: string, initiativeId: string): Promise<TInitiative> {
    return this.unwrap(this.get(this.url(workspaceSlug, `${initiativeId}/`)));
  }

  async create(workspaceSlug: string, data: TInitiativeFormData): Promise<TInitiative> {
    return this.unwrap(this.post(this.url(workspaceSlug), data));
  }

  async update(workspaceSlug: string, initiativeId: string, data: TInitiativeFormData): Promise<TInitiative> {
    return this.unwrap(this.patch(this.url(workspaceSlug, `${initiativeId}/`), data));
  }

  async remove(workspaceSlug: string, initiativeId: string): Promise<void> {
    await this.unwrap(this.delete(this.url(workspaceSlug, `${initiativeId}/`)));
  }

  async linkProjects(workspaceSlug: string, initiativeId: string, projectIds: string[]): Promise<TInitiative> {
    return this.unwrap(this.post(this.url(workspaceSlug, `${initiativeId}/projects/`), { project_ids: projectIds }));
  }

  async unlinkProject(workspaceSlug: string, initiativeId: string, projectId: string): Promise<void> {
    await this.unwrap(this.delete(this.url(workspaceSlug, `${initiativeId}/projects/${projectId}/`)));
  }

  async listEpics(workspaceSlug: string, initiativeId: string): Promise<TInitiativeEpic[]> {
    return this.unwrap(this.get(this.url(workspaceSlug, `${initiativeId}/epics/`)));
  }

  async searchEpics(workspaceSlug: string, initiativeId: string, search: string): Promise<TInitiativeEpicOption[]> {
    return this.unwrap(this.get(this.url(workspaceSlug, `${initiativeId}/epics/search/`), { params: { search } }));
  }

  async linkEpics(workspaceSlug: string, initiativeId: string, epicIds: string[]): Promise<TInitiative> {
    return this.unwrap(this.post(this.url(workspaceSlug, `${initiativeId}/epics/`), { epic_ids: epicIds }));
  }

  async unlinkEpic(workspaceSlug: string, initiativeId: string, epicId: string): Promise<void> {
    await this.unwrap(this.delete(this.url(workspaceSlug, `${initiativeId}/epics/${epicId}/`)));
  }

  async listUpdates(workspaceSlug: string, initiativeId: string): Promise<TInitiativeUpdate[]> {
    return this.unwrap(this.get(this.url(workspaceSlug, `${initiativeId}/updates/`)));
  }

  async createUpdate(
    workspaceSlug: string,
    initiativeId: string,
    data: { health: TInitiativeHealth; text: string }
  ): Promise<TInitiativeUpdate> {
    return this.unwrap(this.post(this.url(workspaceSlug, `${initiativeId}/updates/`), data));
  }
}
