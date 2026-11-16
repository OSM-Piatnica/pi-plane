/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Select } from "@plane/blocks/select";
import type { SelectVariant } from "@plane/blocks/select";
import type { TDepartment } from "@plane/types";
// helpers
import { getDepartmentLabel, sortDepartments } from "@/helpers/department";

export type TDepartmentOption = Pick<TDepartment, "id" | "name" | "code" | "color" | "sort_order">;

type Props = {
  /** The departments offered, in any order. */
  departments: TDepartmentOption[];
  /** The id of the chosen department. */
  value: string | null;
  /** The chosen department when it is not among the ones offered (one that was switched off). */
  current?: TDepartmentOption | null;
  onChange: (departmentId: string | null) => void;
  /** Whether "no department" can be chosen. */
  allowNone?: boolean;
  disabled?: boolean;
  variant?: SelectVariant;
  className?: string;
};

const NONE = "";

export function DepartmentColorDot(props: { color: string }) {
  const { color } = props;
  return (
    <span
      aria-hidden="true"
      className="inline-block size-2.5 shrink-0 rounded-full border border-subtle"
      style={{ backgroundColor: color || "transparent" }}
    />
  );
}

/** A picker of one department. */
export function DepartmentSelect(props: Props) {
  const {
    departments,
    value,
    current,
    onChange,
    allowNone = false,
    disabled,
    variant = "select-md",
    className,
  } = props;
  // translation
  const { t } = useTranslation();
  // derived values
  const options = useMemo(() => {
    const sorted: TDepartmentOption[] = sortDepartments(departments);
    if (current && !sorted.some((department) => department.id === current.id)) sorted.push(current);
    if (!allowNone) return sorted;
    const none: TDepartmentOption = {
      id: NONE,
      name: t("workspace_settings.settings.departments.no_department"),
      code: "",
      color: "",
      sort_order: 0,
    };
    return [none, ...sorted];
  }, [departments, current, allowNone, t]);
  const selected = options.find((department) => department.id === (value ?? NONE)) ?? null;
  const offered = new Set(departments.map((department) => department.id));

  return (
    <Select<TDepartmentOption>
      getValues={() => options}
      value={selected}
      onChange={(id) => onChange(id === NONE ? null : id)}
      getOptionValue={(department) => department.id}
      getOptionLabel={(department) => getDepartmentLabel(department)}
      getOptionIcon={(department) =>
        department.id === NONE ? undefined : <DepartmentColorDot color={department.color} />
      }
      // a department that was switched off is shown as the person's own, and cannot be chosen again
      getOptionDisabled={(department) => department.id !== NONE && !offered.has(department.id)}
      placeholder={t("workspace_settings.settings.departments.select")}
      showSearch={options.length > 8}
      pinSelected={false}
      disabled={disabled}
    >
      <Select.Trigger<TDepartmentOption> variant={variant} className={className}>
        <span className="flex min-w-0 flex-1 items-center gap-2 text-left">
          {selected && selected.id !== NONE && <DepartmentColorDot color={selected.color} />}
          <span className={`min-w-0 truncate ${selected && selected.id !== NONE ? "" : "text-placeholder"}`}>
            {selected ? getDepartmentLabel(selected) : t("workspace_settings.settings.departments.select")}
          </span>
        </span>
      </Select.Trigger>
    </Select>
  );
}
