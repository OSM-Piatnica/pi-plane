/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TShiftCauseLink } from "@/helpers/reschedule";

type TShiftCauseLinkProps = { cause: TShiftCauseLink | undefined };

/** The work item whose date change moved the one an activity entry is about, as a link to it. */
export function ShiftCauseLink(props: TShiftCauseLinkProps) {
  const { cause } = props;

  if (!cause) return null;
  return (
    <a href={cause.href} target="_blank" rel="noopener noreferrer" className="font-medium text-primary hover:underline">
      {cause.ref}
    </a>
  );
}
