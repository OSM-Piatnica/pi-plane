/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";

/**
 * Tells the dialog around a form whether the form holds anything the user entered, so the dialog can
 * ignore outside clicks (and not discard that input) while the form is dirty, and close on them while
 * it is untouched. Reports `false` again when the form unmounts.
 */
export const useReportFormInput = (hasInput: boolean, onInputChange?: (hasInput: boolean) => void) => {
  useEffect(() => {
    onInputChange?.(hasInput);
  }, [hasInput, onInputChange]);
  useEffect(() => () => onInputChange?.(false), [onInputChange]);
};
