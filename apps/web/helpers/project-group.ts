/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EProjectGroupRole } from "@plane/types";
import type { TProjectGroup, TUserGroup } from "@plane/types";

type TMemberGroupFields = {
  via_group?: boolean;
  group_role?: number | null;
  /** Set only while a group lifts the person's role above their own. */
  direct_role?: number | null;
};

/** How groups shape a person's membership: they are in only through a group, or a group raised their role. */
export type TMemberGroupBadge = "via_group" | "raised" | null;

export const getMemberGroupBadge = (member: TMemberGroupFields): TMemberGroupBadge => {
  if (member.via_group) return "via_group";
  // the API keeps the person's own role in `direct_role` exactly while a group lifts them above it
  return member.direct_role === null || member.direct_role === undefined ? null : "raised";
};

/** A person who is in the project only through a group cannot be removed or leave on their own. */
export const isMemberOnlyViaGroup = (member: TMemberGroupFields): boolean => member.via_group === true;

/** The workspace's groups that are not yet members of the project, by name. */
export const getAddableGroups = (groups: TUserGroup[], projectGroups: TProjectGroup[]): TUserGroup[] => {
  const linked = new Set(projectGroups.map((link) => link.group));
  return groups.filter((group) => !linked.has(group.id)).toSorted((a, b) => a.name.localeCompare(b.name));
};

/** Groups can only be Member or Guest in a project, never Admin. */
export const PROJECT_GROUP_ROLES: EProjectGroupRole[] = [EProjectGroupRole.MEMBER, EProjectGroupRole.GUEST];

export const isProjectGroupRole = (role: number): role is EProjectGroupRole =>
  PROJECT_GROUP_ROLES.includes(role as EProjectGroupRole);
