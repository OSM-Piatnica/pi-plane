/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
// helpers
import { cn } from "@plane/utils";

type RadioInputProps = {
  name?: string;
  label?: string | React.ReactNode;
  wrapperClassName?: string;
  fieldClassName?: string;
  buttonClassName?: string;
  labelClassName?: string;
  ariaLabel?: string;
  options: { label: string | React.ReactNode; value: string; disabled?: boolean }[];
  vertical?: boolean;
  selected: string;
  onChange: (value: string) => void;
  className?: string;
};

export function RadioInput({
  name = "radio-input",
  label: inputLabel,
  labelClassName: inputLabelClassName = "",
  wrapperClassName: inputWrapperClassName = "",
  fieldClassName: inputFieldClassName = "",
  buttonClassName: inputButtonClassName = "",
  options,
  vertical,
  selected,
  ariaLabel,
  onChange,
  className,
}: RadioInputProps) {
  const wrapperClass = vertical ? "flex flex-col gap-1" : "flex gap-2";

  const setSelected = (value: string) => {
    onChange(value);
  };

  let aria = ariaLabel ? ariaLabel.toLowerCase().replace(" ", "-") : "";
  if (!aria && typeof inputLabel === "string") {
    aria = inputLabel.toLowerCase().replace(" ", "-");
  } else {
    aria = "radio-input";
  }

  return (
    <div className={className}>
      {inputLabel && <div className={cn(`mb-2`, inputLabelClassName)}>{inputLabel}</div>}
      <div className={cn(`${wrapperClass}`, inputWrapperClassName)}>
        {options.map(({ value, label, disabled }, index) => (
          // oxlint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- existing interactive wrapper; behaviour unchanged
          <div
            // oxlint-disable-next-line react/no-array-index-key -- no stable unique key available
            key={index}
            onClick={() => !disabled && setSelected(value)}
            className={cn(
              "flex items-center gap-2 text-14",
              disabled ? `cursor-not-allowed border-subtle bg-layer-1` : ``,
              inputFieldClassName
            )}
          >
            <input
              id={`${name}_${index}`}
              name={name}
              className={cn(
                `group flex size-5 flex-shrink-0 cursor-pointer items-center justify-center rounded-full border border-strong-1 bg-layer-2`,
                selected === value ? `border-accent-strong bg-accent-primary/80` : ``,
                disabled ? `cursor-not-allowed border-subtle bg-layer-1` : ``,
                inputButtonClassName
              )}
              type="radio"
              value={value}
              disabled={disabled}
              checked={selected === value}
            />
            <label htmlFor={`${name}_${index}`} className="w-full cursor-pointer">
              {label}
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}
