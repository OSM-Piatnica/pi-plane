/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Select } from "@plane/blocks/select";

export type TProjectTemplateSelectOption<T extends string | number> = { value: T; label: string };

type TProps<T extends string | number> = {
  value: T;
  onChange: (value: T) => void;
  options: TProjectTemplateSelectOption<T>[];
  disabled?: boolean;
};

export function ProjectTemplateSelectField<T extends string | number>({
  value,
  onChange,
  options,
  disabled = false,
}: TProps<T>) {
  const selected = options.find((option) => option.value === value) ?? null;
  return (
    <Select<TProjectTemplateSelectOption<T>>
      getValues={() => options}
      value={selected}
      onChange={(next) => {
        const match = options.find((option) => String(option.value) === next);
        if (match) onChange(match.value);
      }}
      getOptionValue={(option) => String(option.value)}
      getOptionLabel={(option) => option.label}
      disabled={disabled}
      showSearch={false}
      pinSelected={false}
    >
      <Select.Trigger variant="select-lg" className="w-full">
        <Select.Value />
      </Select.Trigger>
    </Select>
  );
}
