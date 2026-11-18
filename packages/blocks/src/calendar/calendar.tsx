/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Calendar as PropelCalendar } from "@makeplane/propel/components/calendar";
import type { CalendarProps } from "@makeplane/propel/components/calendar";
import { useCalendarLabels } from "./use-calendar-labels";

/**
 * Propel's `Calendar` with its screen reader names in the interface language. Use this instead of importing propel's
 * directly; a caller's own `labels` win over the translated ones.
 */
export function Calendar({ labels, ...props }: CalendarProps) {
  const translatedLabels = useCalendarLabels();
  return <PropelCalendar {...props} labels={{ ...translatedLabels, ...labels }} />;
}

Calendar.displayName = "blocks.Calendar";
