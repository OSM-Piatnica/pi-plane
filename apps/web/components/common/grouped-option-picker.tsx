/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Checkbox } from "@makeplane/propel/components/checkbox";
// helpers
import type { TOptionGroup } from "@/helpers/option-groups";
import { getGroupSelectionState, getOptionKeys, toggleGroup, toggleOption } from "@/helpers/option-groups";

type Props = {
  groups: TOptionGroup[];
  /** Keys of the options that are switched on. */
  value: string[];
  onChange: (value: string[]) => void;
  /** Id prefix for the checkboxes, so two pickers on one page do not share ids. */
  idPrefix: string;
  selectAllLabel: string;
  clearAllLabel: string;
  disabled?: boolean;
};

/**
 * A list of options in groups, each switched on or off on its own or all at once through its group,
 * plus one link to switch every option on or off. Which options exist, and what they mean, is up to
 * the caller.
 */
export const GroupedOptionPicker = observer(function GroupedOptionPicker(props: Props) {
  const { groups, value, onChange, idPrefix, selectAllLabel, clearAllLabel, disabled = false } = props;
  // derived values
  const allKeys = getOptionKeys(groups);
  const selected = new Set(value);
  const allSelected = allKeys.length > 0 && allKeys.every((key) => selected.has(key));

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => onChange(allSelected ? [] : allKeys)}
          disabled={disabled}
          className="text-13 text-accent-primary hover:underline disabled:text-placeholder disabled:no-underline"
        >
          {allSelected ? clearAllLabel : selectAllLabel}
        </button>
      </div>
      <div className="grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
        {groups.map((group) => {
          const state = getGroupSelectionState(group, value);
          return (
            <fieldset key={group.key} className="flex min-w-0 flex-col gap-2">
              <legend className="sr-only">{group.label}</legend>
              <Checkbox
                id={`${idPrefix}-group-${group.key}`}
                label={group.label}
                checked={state === "all"}
                indeterminate={state === "some"}
                onCheckedChange={() => onChange(toggleGroup(group, value))}
                disabled={disabled}
              />
              <div className="flex flex-col gap-2 pl-6">
                {group.options.map((option) => (
                  <Checkbox
                    key={option.key}
                    id={`${idPrefix}-${option.key}`}
                    label={option.label}
                    checked={selected.has(option.key)}
                    onCheckedChange={() => onChange(toggleOption(option.key, value))}
                    disabled={disabled}
                  />
                ))}
              </div>
            </fieldset>
          );
        })}
      </div>
    </div>
  );
});
