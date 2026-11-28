/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
import type { TRaciRole } from "@plane/types";
import { getRaciChipLabel, getRaciChipTextColor } from "@plane/utils";
import type { TRaciDepartment } from "@plane/utils";

type Props = {
  department: Pick<TRaciDepartment, "name" | "code" | "color">;
  /** The role to show as its letter in the chip; leave out for the department alone. */
  role?: TRaciRole | null;
};

/** A department as a coloured chip with its code; with a role, the letter of the role follows it. */
export function RaciChip(props: Props) {
  const { department, role } = props;
  // translation
  const { t } = useTranslation();
  const color = department.color || undefined;
  const label = role ? `${department.name} · ${t(`raci.roles.${role}.name`)}` : department.name;

  return (
    <Tooltip label={label}>
      <span
        className="inline-flex h-5 items-center gap-1 rounded-sm border border-subtle bg-layer-1 px-1.5 text-11 font-medium text-primary"
        style={color ? { backgroundColor: color, color: getRaciChipTextColor(color), borderColor: color } : undefined}
      >
        {getRaciChipLabel(department)}
        {role && <span className="font-semibold">{t(`raci.roles.${role}.letter`)}</span>}
      </span>
    </Tooltip>
  );
}
