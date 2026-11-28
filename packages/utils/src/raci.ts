/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { RACI_FILTER_MY_DEPARTMENT } from "@plane/constants";
import { RACI_ROLES } from "@plane/types";
import type { TDepartment, TIssueRaciEntry, TRaciRole } from "@plane/types";
// local imports
import { getLuminance } from "./color";

export type TRaciTranslate = (key: string, params?: Record<string, string | number>) => string;

/** A department as the RACI chips and pickers need it. */
export type TRaciDepartment = Pick<TDepartment, "id" | "name" | "code" | "color" | "sort_order" | "is_active">;

const ROLE_SET = new Set<string>(RACI_ROLES);

export const isRaciRole = (value: unknown): value is TRaciRole => typeof value === "string" && ROLE_SET.has(value);

/** The translation key of the letter of a role (R / A / C / I in English, O / Z / K / I in Polish). */
export const getRaciLetterKey = (role: TRaciRole): string => `raci.roles.${role}.letter`;

/** The translation key of the full name of a role. */
export const getRaciNameKey = (role: TRaciRole): string => `raci.roles.${role}.name`;

/** The role a department has in a list of entries, or null. */
export const getRaciRole = (entries: TIssueRaciEntry[] | undefined, groupId: string): TRaciRole | null =>
  entries?.find((entry) => entry.group_id === groupId)?.role ?? null;

/**
 * The entries after one department was given a role, or lost it (null). A department has one role on a
 * work item, so its earlier entry is replaced; the other departments keep their place.
 */
export const setRaciRole = (
  entries: TIssueRaciEntry[] | undefined,
  groupId: string,
  role: TRaciRole | null
): TIssueRaciEntry[] => {
  const others = (entries ?? []).filter((entry) => entry.group_id !== groupId);
  return role ? [...others, { group_id: groupId, role }] : others;
};

/** Entries as the API takes them: known roles only, and the last entry of a department wins. */
export const sanitizeRaci = (entries: TIssueRaciEntry[] | undefined): TIssueRaciEntry[] => {
  const byGroup = new Map<string, TRaciRole>();
  for (const entry of entries ?? []) {
    if (entry?.group_id && isRaciRole(entry.role)) byGroup.set(entry.group_id, entry.role);
  }
  return [...byGroup].map(([group_id, role]) => ({ group_id, role }));
};

/** Whether two lists name the same departments with the same roles, in any order. */
export const isSameRaci = (a: TIssueRaciEntry[] | undefined, b: TIssueRaciEntry[] | undefined): boolean => {
  const left = sanitizeRaci(a);
  const right = new Map(sanitizeRaci(b).map((entry) => [entry.group_id, entry.role]));
  return left.length === right.size && left.every((entry) => right.get(entry.group_id) === entry.role);
};

/**
 * The departments that have the given role, in the order departments are listed (their place, then their name).
 * A department that is not known (deleted since, or not loaded yet) is left out.
 */
export const getRaciDepartments = <T extends Pick<TRaciDepartment, "id" | "name" | "sort_order">>(
  entries: TIssueRaciEntry[] | undefined,
  role: TRaciRole,
  departmentsById: Map<string, T>
): T[] =>
  (entries ?? [])
    .filter((entry) => entry.role === role)
    .flatMap((entry) => {
      const department = departmentsById.get(entry.group_id);
      return department ? [department] : [];
    })
    .toSorted((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));

/**
 * The departments a RACI editor lists: the ones that are switched on, and the ones switched off that still have a
 * role here (so the role can be seen and taken away). In the order departments are listed.
 */
export const getRaciEditorDepartments = <T extends Pick<TRaciDepartment, "id" | "name" | "sort_order" | "is_active">>(
  departments: T[],
  entries: TIssueRaciEntry[] | undefined
): T[] => {
  const withRole = new Set((entries ?? []).map((entry) => entry.group_id));
  return departments
    .filter((department) => department.is_active !== false || withRole.has(department.id))
    .toSorted((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));
};

/** "RM", or the name of a department without a code. */
export const getRaciChipLabel = (department: Pick<TRaciDepartment, "name" | "code">): string =>
  department.code || department.name;

/**
 * Who may change the roles on a work item: an admin of the project, and the project lead.
 * The API decides; this only keeps the pickers of everybody else read-only.
 */
export const canEditRaci = (args: {
  isProjectAdmin: boolean;
  projectLead: { id: string } | string | null | undefined;
  userId: string | undefined;
}): boolean => {
  const { isProjectAdmin, projectLead, userId } = args;
  if (isProjectAdmin) return true;
  if (!userId || !projectLead) return false;
  return (typeof projectLead === "string" ? projectLead : projectLead.id) === userId;
};

/**
 * The CSS background of a timeline bar coloured by the responsible departments: one colour, or equal
 * stripes side by side when several departments answer for the work item together. Undefined without a colour.
 */
export const getRaciBarBackground = (colors: (string | undefined | null)[]): string | undefined => {
  const usable = colors.filter((color): color is string => !!color);
  if (usable.length === 0) return undefined;
  if (usable.length === 1) return usable[0];
  const step = 100 / usable.length;
  const stops = usable.map((color, index) => `${color} ${index * step}% ${(index + 1) * step}%`);
  return `linear-gradient(90deg, ${stops.join(", ")})`;
};

const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i;
const CHIP_TEXT_DARK = "#1f2937";
const CHIP_TEXT_LIGHT = "#ffffff";

/**
 * The text colour that reads on a chip filled with the colour of a department: dark on light colours, white on
 * dark ones. Undefined when the department has no (usable) colour, so the chip keeps the colours of the theme.
 */
export const getRaciChipTextColor = (color: string | undefined | null): string | undefined => {
  if (!color || !HEX_COLOR.test(color)) return undefined;
  const digits = color.slice(1);
  const full = digits.length === 3 ? [...digits].map((digit) => digit + digit).join("") : digits;
  const [r, g, b] = [0, 2, 4].map((start) => Number.parseInt(full.slice(start, start + 2), 16));
  return getLuminance({ r, g, b }) > 0.4 ? CHIP_TEXT_DARK : CHIP_TEXT_LIGHT;
};

// ------------ filters ------------

export const RACI_FILTER_ANY_ROLE_KEY = "raci_department_id";

/** The role a RACI filter property stands for; null for the one that matches any role, undefined for other keys. */
export const getRaciFilterRole = (property: string): TRaciRole | null | undefined => {
  if (property === RACI_FILTER_ANY_ROLE_KEY) return null;
  const match = /^raci_([a-z]+)_id$/.exec(property);
  return match && isRaciRole(match[1]) ? match[1] : undefined;
};

export type TRaciFilterOption = {
  /** A department id, or RACI_FILTER_MY_DEPARTMENT. */
  value: string;
  label: string;
  /** The colour of the department; empty for "My department" and departments without one. */
  color: string;
  isKeyword: boolean;
};

/**
 * The options of a RACI filter: "My department" first, then the departments in the order they are listed.
 * @param departments - The departments of the workspace
 * @param t - Translates the label of "My department", it stays English without it
 */
export const getRaciFilterOptions = (departments: TRaciDepartment[], t?: TRaciTranslate): TRaciFilterOption[] => [
  {
    value: RACI_FILTER_MY_DEPARTMENT,
    label: t ? t("raci.my_department") : "My department",
    color: "",
    isKeyword: true,
  },
  ...departments
    .toSorted((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
    .map((department) => ({
      value: department.id,
      label: department.code ? `${department.code} · ${department.name}` : department.name,
      color: department.color,
      isKeyword: false,
    })),
];
