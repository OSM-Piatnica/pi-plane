/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueType, TProjectIssueType } from "@plane/types";
import { isEpicKind, isSystemManagedType } from "@plane/utils";

type TSelectableOptions = {
  /** Offer the system-managed kinds (approval, review) as well. Off unless a caller has a reason to ask. */
  includeSystemManaged?: boolean;
};

/**
 * The types of a project that a person can pick for a work item. Types of a system-managed kind are left out:
 * the system creates those work items, and the server refuses a switch into or out of the kind.
 * Epic types are offered like any other type: choosing the Epic type is how an Epic is made.
 */
export const getSelectableProjectIssueTypes = (
  rows: TProjectIssueType[],
  options: TSelectableOptions = {}
): TProjectIssueType[] =>
  rows.filter(
    (row) => !!row.issue_type_detail && (options.includeSystemManaged || !isSystemManagedType(row.issue_type_detail))
  );

/** The type a new work item starts with: the project default, else the first one a person can pick. */
export const getDefaultProjectIssueTypeId = (rows: TProjectIssueType[]): string | null => {
  const selectable = getSelectableProjectIssueTypes(rows);
  return (selectable.find((row) => row.is_default) ?? selectable[0])?.issue_type_id ?? null;
};

/**
 * The link of the type a work item has, when that type is system-managed. Such a work item shows its type
 * read-only: there is nothing a person can switch it to.
 */
export const getLockedProjectIssueType = (
  rows: TProjectIssueType[],
  typeId: string | null | undefined
): TProjectIssueType | null => {
  if (!typeId) return null;
  const row = rows.find((item) => item.issue_type_id === typeId);
  return row && isSystemManagedType(row.issue_type_detail) ? row : null;
};

type TAssignableOptions = {
  /** Leave Epic types out, where Epics have a switch of their own */
  hideEpics?: boolean;
};

/**
 * Workspace types that a generic type list (project settings, project creation) may link to or unlink from a
 * project. Types of a system-managed kind are linked by the feature that uses them, never by hand.
 */
export const getAssignableIssueTypes = (rows: TIssueType[], options: TAssignableOptions = {}): TIssueType[] =>
  rows.filter((row) => !isSystemManagedType(row) && !(options.hideEpics && isEpicKind(row)));

/**
 * The default type to send with a bulk assignment: the current default while it stays in the list, else the
 * first type of the list that is not system-managed. Null when there is none, and the server then leaves the
 * default as it is.
 */
export const getBulkAssignDefaultTypeId = (
  typeIds: string[],
  linked: TProjectIssueType[],
  currentDefaultId: string | null | undefined
): string | null => {
  if (currentDefaultId && typeIds.includes(currentDefaultId)) return currentDefaultId;
  const systemManaged = new Set(
    linked.filter((row) => isSystemManagedType(row.issue_type_detail)).map((row) => row.issue_type_id)
  );
  return typeIds.find((id) => !systemManaged.has(id)) ?? null;
};

/** Names of the workspace's system-managed types: a project template cannot bring these in by name. */
export const getSystemManagedTypeNames = (rows: TIssueType[]): string[] =>
  rows.filter((row) => isSystemManagedType(row)).map((row) => row.name.trim());

/** The server finds a template's type by its exact name, so the match here is exact as well. */
export const isSystemManagedTypeName = (name: string, systemManagedNames: string[]): boolean =>
  !!name.trim() && systemManagedNames.includes(name.trim());
