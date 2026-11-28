/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  TIssueRaci,
  TIssueRaciEntry,
  TRaciNotificationMatrix,
  TRaciNotificationPreview,
  TRaciNotificationSettings,
  TRaciProjectWarnings,
} from "@plane/types";
import { APIService } from "@/services/api.service";

export class IssueRaciService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /** The roles of the departments on a work item, and whether the requester may change them. */
  async getRaci(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueRaci> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/raci/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Replaces every role on a work item: a department that is left out loses its role. */
  async setRaci(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    raci: TIssueRaciEntry[]
  ): Promise<TIssueRaci> {
    return this.put(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/raci/`, { raci })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Who the roles on a work item make hear about each event of the workspace's notification matrix. */
  async getNotificationPreview(
    workspaceSlug: string,
    projectId: string,
    issueId: string
  ): Promise<TRaciNotificationPreview> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/raci/notifications/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** The RACI warnings of a project. */
  async getProjectWarnings(workspaceSlug: string, projectId: string): Promise<TRaciProjectWarnings> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/raci-warnings/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** The notification matrix of a workspace: which roles hear about which event. */
  async getNotificationSettings(workspaceSlug: string): Promise<TRaciNotificationSettings> {
    return this.get(`/api/workspaces/${workspaceSlug}/raci-notifications/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Stores the events given; the others keep what they have (workspace admins). */
  async updateNotificationSettings(
    workspaceSlug: string,
    matrix: Partial<TRaciNotificationMatrix>
  ): Promise<TRaciNotificationSettings> {
    return this.patch(`/api/workspaces/${workspaceSlug}/raci-notifications/`, { matrix })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

export const issueRaciService = new IssueRaciService();
