/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { EUserGroupRole, TUserGroup, TUserGroupFormData, TUserGroupMember } from "@plane/types";
import { APIService } from "@/services/api.service";

export class UserGroupService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(workspaceSlug: string): Promise<TUserGroup[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/user-groups/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(workspaceSlug: string, data: TUserGroupFormData): Promise<TUserGroup> {
    return this.post(`/api/workspaces/${workspaceSlug}/user-groups/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(workspaceSlug: string, groupId: string, data: Partial<TUserGroupFormData>): Promise<TUserGroup> {
    return this.patch(`/api/workspaces/${workspaceSlug}/user-groups/${groupId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, groupId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/user-groups/${groupId}/`)
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async listMembers(workspaceSlug: string, groupId: string, nested = false): Promise<TUserGroupMember[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/user-groups/${groupId}/members/`, {
      params: nested ? { nested: "true" } : undefined,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addMember(
    workspaceSlug: string,
    groupId: string,
    data: { user_id: string; role: EUserGroupRole }
  ): Promise<TUserGroupMember> {
    return this.post(`/api/workspaces/${workspaceSlug}/user-groups/${groupId}/members/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateMemberRole(
    workspaceSlug: string,
    groupId: string,
    userId: string,
    role: EUserGroupRole
  ): Promise<TUserGroupMember> {
    return this.patch(`/api/workspaces/${workspaceSlug}/user-groups/${groupId}/members/${userId}/`, { role })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeMember(workspaceSlug: string, groupId: string, userId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/user-groups/${groupId}/members/${userId}/`)
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

export const userGroupService = new UserGroupService();
