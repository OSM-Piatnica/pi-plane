/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TNotificationAccessRequest } from "@plane/types";

type TStatus = TNotificationAccessRequest["status"];

/** The inbox text about a request to join a Private project: to the admins it is open, to the requester decided. */
export const getAccessRequestNotificationTextKey = (status: TStatus) => {
  if (status === "approved") return "notification.access_request.approved";
  if (status === "rejected") return "notification.access_request.rejected";
  return "notification.access_request.requested";
};

/**
 * Where a click on that inbox entry leads: the admins to the members settings where the request waits, a
 * requester whose request was approved into the project, and one whose request was rejected to the project list.
 */
export const getAccessRequestNotificationPath = (status: TStatus, workspaceSlug: string, projectId: string) => {
  if (status === "approved") return `/${workspaceSlug}/projects/${projectId}/issues/`;
  if (status === "rejected") return `/${workspaceSlug}/projects/`;
  return `/${workspaceSlug}/settings/projects/${projectId}/members/`;
};
