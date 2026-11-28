/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserPermissions } from "@plane/constants";
import { EUserWorkspaceRoles } from "@plane/types";
import type { TInitiative, TInitiativeProgress } from "@plane/types";

/** The share of the work items that are done (completed or cancelled), as a whole percentage */
export const getInitiativeProgressPercentage = (progress: TInitiativeProgress | undefined): number => {
  if (!progress || progress.total_issues <= 0) return 0;
  return Math.floor(((progress.completed + progress.cancelled) / progress.total_issues) * 100);
};

const byPosition = (a: TInitiative, b: TInitiative) =>
  a.sort_order - b.sort_order || b.created_at.localeCompare(a.created_at);

export type TInitiativeTreeNode = {
  /** The goal, or undefined for the initiatives that have no goal */
  goal: TInitiative | undefined;
  initiatives: TInitiative[];
};

/**
 * The goals with their initiatives, in list order, then the initiatives without a goal (and those
 * whose goal is not in the list). Used by the sidebar tree and the grouped list.
 */
export const buildInitiativeTree = (items: readonly TInitiative[]): TInitiativeTreeNode[] => {
  const goals = items.filter((item) => item.kind === "goal").toSorted(byPosition);
  const goalIds = new Set(goals.map((goal) => goal.id));
  const initiatives = items.filter((item) => item.kind === "initiative").toSorted(byPosition);
  const nodes: TInitiativeTreeNode[] = goals.map((goal) => ({
    goal,
    initiatives: initiatives.filter((item) => item.parent === goal.id),
  }));
  const loose = initiatives.filter((item) => !item.parent || !goalIds.has(item.parent));
  if (loose.length > 0) nodes.push({ goal: undefined, initiatives: loose });
  return nodes;
};

/** Deleting is for a workspace admin, the lead and the person who created it (as the API decides) */
export const canDeleteInitiative = (
  initiative: Pick<TInitiative, "lead" | "created_by">,
  userId: string | undefined,
  workspaceRole: EUserWorkspaceRoles | number | undefined
): boolean => {
  if (workspaceRole === EUserWorkspaceRoles.ADMIN) return true;
  if (!userId || workspaceRole !== EUserWorkspaceRoles.MEMBER) return false;
  return initiative.lead === userId || initiative.created_by === userId;
};

/**
 * Whether the person may link or unlink a project or its Epics: a workspace admin always, anybody
 * else with at least the Member role in the project. Mirrors `project_access` in the API, which
 * has the last word.
 */
export const canLinkInProject = (
  workspaceRole: EUserWorkspaceRoles | number | undefined,
  projectRole: EUserPermissions | number | undefined
): boolean => {
  if (workspaceRole === EUserWorkspaceRoles.ADMIN) return true;
  return projectRole !== undefined && projectRole >= EUserPermissions.MEMBER;
};

/**
 * The message of a failed initiative request: the API answers `{ error }` or, for a refused
 * field, `{ field: [message] }`. Anything else gets the general message.
 */
export const getInitiativeErrorMessage = (error: unknown, t: (key: string) => string): string => {
  if (error && typeof error === "object") {
    const body = error as Record<string, unknown>;
    if (typeof body.error === "string") return body.error;
    for (const value of Object.values(body)) {
      if (typeof value === "string") return value;
      if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    }
  }
  return t("initiatives.toast.error");
};
