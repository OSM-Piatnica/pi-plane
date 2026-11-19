/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TDepartment, TUserGroup } from "@plane/types";

/** The longest code the server stores. */
export const DEPARTMENT_CODE_MAX_LENGTH = 16;
export const DEPARTMENT_NAME_MAX_LENGTH = 255;
/** The colours offered for a department; any hex colour can be typed in as well. */
export const DEPARTMENT_COLORS = [
  "#3f76ff",
  "#0ea5e9",
  "#14b8a6",
  "#22c55e",
  "#84cc16",
  "#eab308",
  "#f97316",
  "#ef4444",
  "#ec4899",
  "#a855f7",
  "#6366f1",
  "#78716c",
  "#64748b",
];
const SORT_ORDER_STEP = 10000;

/** The SWR key of the departments that are switched on (the list for pickers). */
export const getDepartmentsKey = (workspaceSlug: string) => `WORKSPACE_DEPARTMENTS_${workspaceSlug}`;
/** The SWR key of who works in which department (derived from the department groups). */
export const getDepartmentMembersKey = (workspaceSlug: string) => `WORKSPACE_DEPARTMENT_MEMBERS_${workspaceSlug}`;
/** The SWR key of every group of the workspace (shared with the groups settings). */
export const getUserGroupsKey = (workspaceSlug: string) => `USER_GROUPS_${workspaceSlug}`;
const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i;

export type TDepartmentImportRow = { code: string; name: string };
export type TDepartmentImportProblem = "empty_name" | "code_too_long" | "name_too_long" | "duplicate";
export type TDepartmentImportSkipped = { line: number; text: string; problem: TDepartmentImportProblem };
export type TDepartmentImportParsed = { rows: TDepartmentImportRow[]; skipped: TDepartmentImportSkipped[] };
export type TDepartmentImportPlan = {
  /** Rows that become new departments, in the order of the list. */
  create: TDepartmentImportRow[];
  /** Rows left out because a department with that code or name is already there. */
  existing: TDepartmentImportRow[];
};

/** Codes are compared and stored in upper case, without the spaces around them (as the server does). */
export const normalizeDepartmentCode = (code: string): string => code.trim().toUpperCase();

export const isDepartmentColor = (color: string): boolean => color === "" || HEX_COLOR.test(color);

/**
 * Reads a pasted list of departments, one per line: "CODE;Name". A tab works as the separator too
 * (a list copied from a spreadsheet), and a line without a separator is a department without a code.
 * Empty lines are passed over; a line that cannot be used is reported with its number.
 */
export function parseDepartmentList(text: string): TDepartmentImportParsed {
  const rows: TDepartmentImportRow[] = [];
  const skipped: TDepartmentImportSkipped[] = [];
  const seenCodes = new Set<string>();
  const seenNames = new Set<string>();
  const lines = text.split(/\r?\n/);
  for (const [index, raw] of lines.entries()) {
    const line = raw.trim();
    if (line) {
      const separator = line.search(/[;\t]/);
      const code = separator === -1 ? "" : normalizeDepartmentCode(line.slice(0, separator));
      const name = (separator === -1 ? line : line.slice(separator + 1)).trim();
      const skip = (problem: TDepartmentImportProblem) => skipped.push({ line: index + 1, text: line, problem });
      if (!name) skip("empty_name");
      else if (code.length > DEPARTMENT_CODE_MAX_LENGTH) skip("code_too_long");
      else if (name.length > DEPARTMENT_NAME_MAX_LENGTH) skip("name_too_long");
      else if ((code && seenCodes.has(code)) || seenNames.has(name.toLowerCase())) skip("duplicate");
      else {
        if (code) seenCodes.add(code);
        seenNames.add(name.toLowerCase());
        rows.push({ code, name });
      }
    }
  }
  return { rows, skipped };
}

/**
 * Which rows of a parsed list become departments. A row is left out when a department already has its code, or
 * when a top-level group already has its name (departments are created at the top level, where names are unique).
 */
export function planDepartmentImport(
  rows: TDepartmentImportRow[],
  groups: Pick<TUserGroup, "name" | "code" | "kind" | "parent">[]
): TDepartmentImportPlan {
  const codes = new Set(
    groups.filter((group) => group.kind === "department" && group.code).map((group) => group.code.toUpperCase())
  );
  const names = new Set(groups.filter((group) => group.parent === null).map((group) => group.name.toLowerCase()));
  const plan: TDepartmentImportPlan = { create: [], existing: [] };
  for (const row of rows) {
    if ((row.code && codes.has(row.code)) || names.has(row.name.toLowerCase())) plan.existing.push(row);
    else plan.create.push(row);
  }
  return plan;
}

/** Departments in the order they are listed and offered: by their place, then by name. */
export function sortDepartments<T extends { name: string; sort_order: number }>(departments: T[]): T[] {
  return departments.toSorted((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));
}

/**
 * The place a department gets when it is moved one step up (-1) or down (1) in a sorted list: between its new
 * neighbours. Null when it is already at that end of the list.
 */
export function getMovedSortOrder(
  sorted: { id: string; sort_order: number }[],
  id: string,
  direction: -1 | 1
): number | null {
  const index = sorted.findIndex((department) => department.id === id);
  const target = index + direction;
  if (index === -1 || target < 0 || target >= sorted.length) return null;
  const near = sorted[target];
  const far = sorted[target + direction];
  if (!near) return null;
  if (!far) return near.sort_order + direction * SORT_ORDER_STEP;
  return (near.sort_order + far.sort_order) / 2;
}

/** "RM · Marketing", or the name alone for a department without a code. */
export const getDepartmentLabel = (department: Pick<TDepartment, "name" | "code">): string =>
  department.code ? `${department.code} · ${department.name}` : department.name;
