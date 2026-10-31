/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { CalendarOutline, DueDateOutline, StartDateOutline } from "@makeplane/propel/icons";
// plane imports
import type { TStateGroups } from "@plane/types";
import { cn, shouldHighlightIssueDueDate } from "@plane/utils";
import { useLocalizedDates } from "@/hooks/use-localized-dates";
import { useTranslation } from "@plane/i18n";

type Props = {
  startDate: string | null;
  stateGroup: TStateGroups;
  /** The schedule end. */
  finishDate: string | null;
  /** The due date, which only drives the overdue highlight. */
  targetDate: string | null;
};

export function WorkItemPreviewCardDate(props: Props) {
  const { startDate, stateGroup, finishDate, targetDate } = props;
  const { t } = useTranslation();
  const { formatDate } = useLocalizedDates();
  // derived values
  const endDate = finishDate ?? targetDate;
  const isDateRangeEnabled = Boolean(startDate && endDate);
  const shouldHighlightDate = shouldHighlightIssueDueDate(targetDate, stateGroup);

  if (!startDate && !endDate) return null;

  return (
    <div className="h-full rounded-sm px-1 text-11 text-secondary">
      {isDateRangeEnabled ? (
        <div
          className={cn("flex h-full items-center gap-1", {
            "text-danger-primary": shouldHighlightDate,
          })}
        >
          <CalendarOutline className="size-3 shrink-0" />
          <span>{t("date_phrases.date_range", { start: formatDate(startDate), end: formatDate(endDate) })}</span>
        </div>
      ) : startDate ? (
        <div className="flex h-full items-center gap-1">
          <StartDateOutline className="size-3 shrink-0" />
          <span>{formatDate(startDate)}</span>
        </div>
      ) : (
        <div
          className={cn("flex h-full items-center gap-1", {
            "text-danger-primary": shouldHighlightDate,
          })}
        >
          <DueDateOutline className="size-3 shrink-0" />
          <span>{formatDate(endDate)}</span>
        </div>
      )}
    </div>
  );
}
