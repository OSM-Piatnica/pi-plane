/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TIssueRaciEntry, TTimelineColorBy } from "@plane/types";
import { getRaciBarBackground, getRaciDepartments } from "@plane/utils";
// hooks
import { useDepartments } from "@/hooks/use-departments";

/**
 * The colours of a timeline bar coloured by its responsible departments (RACI): `colors` in department order for
 * the bar colour, and `backgroundImage`, stripes side by side, when several responsible departments have one.
 * Departments are only read while the bars are coloured by them.
 */
export const useRaciBarColors = (
  workspaceSlug: string | undefined,
  colorBy: TTimelineColorBy | undefined,
  raci: TIssueRaciEntry[] | undefined
): { colors: string[]; backgroundImage: string | undefined } => {
  const isColoredByDepartment = colorBy === "department";
  const { departmentsById } = useDepartments(workspaceSlug, isColoredByDepartment);
  if (!isColoredByDepartment) return { colors: [], backgroundImage: undefined };
  const colors = getRaciDepartments(raci, "responsible", departmentsById).map((department) => department.color);
  const background = getRaciBarBackground(colors);
  return { colors, backgroundImage: background?.startsWith("linear-gradient") ? background : undefined };
};
