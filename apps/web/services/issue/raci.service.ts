/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TIssueRaci, TIssueRaciEntry } from "@plane/types";
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
}

export const issueRaciService = new IssueRaciService();
