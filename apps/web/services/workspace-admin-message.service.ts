/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

export type TWorkspaceAdminMessageResult = { id: string; recipients: number };

export class WorkspaceAdminMessageService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /** Write to the admins of the workspace; they get it in their inbox and by email. */
  async send(workspaceSlug: string, message: string): Promise<TWorkspaceAdminMessageResult> {
    return this.post(`/api/workspaces/${workspaceSlug}/admin-messages/`, { message })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }
}

export const workspaceAdminMessageService = new WorkspaceAdminMessageService();
