/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import type { TIssue, TRaciRole } from "@plane/types";
import { getRaciDepartments } from "@plane/utils";
// hooks
import { useDepartments } from "@/hooks/use-departments";
// local imports
import { RaciChip } from "./raci-chip";

type Props = {
  issue: Pick<TIssue, "raci">;
  role: TRaciRole;
  className?: string;
};

/** The departments that have one role on a work item, as chips: a cell of a list or a spreadsheet. */
export const RaciRolesCell = observer(function RaciRolesCell(props: Props) {
  const { issue, role, className } = props;
  // router
  const { workspaceSlug } = useParams();
  // the list is only asked for when a work item has a role at all
  const hasRoles = (issue.raci?.length ?? 0) > 0;
  const { departmentsById } = useDepartments(workspaceSlug?.toString(), hasRoles);
  const departments = getRaciDepartments(issue.raci, role, departmentsById);

  if (departments.length === 0) return null;
  return (
    <div className={className ?? "flex flex-wrap items-center gap-1"}>
      {departments.map((department) => (
        <RaciChip key={department.id} department={department} />
      ))}
    </div>
  );
});
