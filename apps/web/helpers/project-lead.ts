/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IUserLite } from "@plane/types";

/** Whether the user is the project's lead. The API sends the lead as a user object; older data may hold only the id. */
export const isProjectLead = (
  projectLead: IUserLite | string | null | undefined,
  userId: string | undefined
): boolean => {
  if (!projectLead || !userId) return false;
  return (typeof projectLead === "string" ? projectLead : projectLead.id) === userId;
};
