/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// types
import type { TIssue, TRaciRole } from "@plane/types";
// components
import { RaciRolesCell } from "@/components/issues/raci/raci-roles-cell";

type Props = {
  issue: TIssue;
  onClose: () => void;
  onChange: (issue: TIssue, data: Partial<TIssue>, updates: any) => void;
  disabled: boolean;
};

const createRaciColumn = (role: TRaciRole) =>
  observer(function SpreadsheetRaciColumn(props: Props) {
    const { issue } = props;
    return (
      <div className="flex h-11 w-full items-center border-b-[0.5px] border-subtle px-page-x">
        <RaciRolesCell issue={issue} role={role} />
      </div>
    );
  });

/** The departments that are responsible, approve or are consulted on a work item. */
export const SpreadsheetRaciResponsibleColumn = createRaciColumn("responsible");
export const SpreadsheetRaciApproverColumn = createRaciColumn("approver");
export const SpreadsheetRaciConsultedColumn = createRaciColumn("consulted");
