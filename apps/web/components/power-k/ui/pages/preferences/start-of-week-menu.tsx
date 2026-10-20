/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { Command } from "cmdk";
// plane imports
import { START_OF_THE_WEEK_OPTIONS } from "@plane/constants";
import type { EStartOfTheWeek } from "@plane/types";
// hooks
import { useCalendarLocale } from "@/hooks/use-calendar-locale";
// local imports
import { PowerKModalCommandItem } from "../../modal/command-item";

type Props = {
  onSelect: (day: EStartOfTheWeek) => void;
};

export function PowerKPreferencesStartOfWeekMenu(props: Props) {
  const { onSelect } = props;
  // hooks
  const { getWeekdayName } = useCalendarLocale();

  return (
    <Command.Group>
      {START_OF_THE_WEEK_OPTIONS.map((day) => (
        <PowerKModalCommandItem
          key={day.value}
          onSelect={() => onSelect(day.value)}
          label={getWeekdayName(day.value)}
        />
      ))}
    </Command.Group>
  );
}
