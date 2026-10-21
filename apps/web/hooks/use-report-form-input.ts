/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isEqual } from "lodash-es";
import { useEffect } from "react";

/**
 * Tells the dialog around a form whether the form holds anything the user entered, so the dialog can
 * ask before an outside click discards that input, and close on it while the form is untouched.
 * Reports `false` again when the form unmounts.
 */
export const useReportFormInput = (hasInput: boolean, onInputChange?: (hasInput: boolean) => void) => {
  useEffect(() => {
    onInputChange?.(hasInput);
  }, [hasInput, onInputChange]);
  useEffect(() => () => onInputChange?.(false), [onInputChange]);
};

const isBlank = (value: unknown) =>
  value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);

const normalize = (value: unknown) => (Array.isArray(value) ? value.toSorted() : value);

/**
 * Whether `current` differs from `baseline` in any of `keys`, treating null, undefined, "" and [] as the
 * same empty value. Unlike react-hook-form's `isDirty`, a field that was typed into and cleared again
 * counts as unchanged.
 */
export const hasInputChanged = <T extends object>(current: Partial<T>, baseline: Partial<T>, keys: (keyof T)[]) =>
  keys.some((key) => {
    const currentValue = current[key];
    const baselineValue = baseline[key];
    if (isBlank(currentValue) && isBlank(baselineValue)) return false;
    return !isEqual(normalize(currentValue), normalize(baselineValue));
  });
