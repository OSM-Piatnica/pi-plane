/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** The colour of a department, as a small dot in front of its name. */
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
