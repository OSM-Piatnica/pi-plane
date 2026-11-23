/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  EUserGroupRole,
  TDepartment,
  TDepartmentMembers,
  TFilterableUserGroup,
  TUserGroup,
  TUserGroupFormData,
  TUserGroupKind,
  TUserGroupMember,
} from "@plane/types";
import { APIService } from "@/services/api.service";

export class UserGroupService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /** Every group of the workspace, or only the groups of one kind (departments come in their own order). */
  async list(workspaceSlug: string, kind?: TUserGroupKind): Promise<TUserGroup[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/user-groups/`, { params: kind ? { kind } : undefined })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** The departments that are switched on, in their order; open to every member of the workspace, guests included. */
  async listDepartments(workspaceSlug: string): Promise<TDepartment[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/departments/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Who works in which department: user id to department (group) id. Guests only get their own. */
  async listDepartmentMembers(workspaceSlug: string): Promise<TDepartmentMembers> {
    return this.get(`/api/workspaces/${workspaceSlug}/departments/members/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** The groups the requester may filter by: every group for a workspace admin, their own and the ones above for others. */
  async listFilterable(workspaceSlug: string): Promise<TFilterableUserGroup[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/user-groups/filterable/`)
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
