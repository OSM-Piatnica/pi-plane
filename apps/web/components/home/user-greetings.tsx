/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
// plane types
import { useTranslation } from "@plane/i18n";
import type { IUser } from "@plane/types";
// plane ui
// hooks
import { formatGreetingDate } from "@/helpers/greeting-date";
import { useCalendarLocale } from "@/hooks/use-calendar-locale";
import { useCurrentTime } from "@/hooks/use-current-time";

export interface IUserGreetingsView {
  user: IUser;
}

export function UserGreetingsView(props: IUserGreetingsView) {
  const { user } = props;
  // current time hook
  const { currentTime } = useCurrentTime();
  // store hooks
  const { t } = useTranslation();

  // The weekday, date and clock follow the user's language ("Monday, Oct 19" in English, "poniedziałek, 19 paź" in Polish).
  const { intlLocale } = useCalendarLocale();
  const hour = useMemo(
    () => new Intl.DateTimeFormat("en-US", { hour12: false, hour: "numeric" }).format(currentTime),
    [currentTime]
  );
  const {
    weekDay,
    date,
    time: timeString,
  } = useMemo(
    () => formatGreetingDate(intlLocale, currentTime, user?.user_timezone),
    [intlLocale, currentTime, user?.user_timezone]
  );

  const greeting = parseInt(hour, 10) < 12 ? "morning" : parseInt(hour, 10) < 18 ? "afternoon" : "evening";

  return (
    <div className="my-6 flex flex-col items-center">
      <h2 className="text-center text-20 font-semibold">
        {t("good")} {t(greeting)}, {user?.first_name} {user?.last_name}
      </h2>
      <h5 className="flex items-center gap-2 font-medium text-placeholder">
        <div>{greeting === "morning" ? "🌤️" : greeting === "afternoon" ? "🌥️" : "🌙️"}</div>
        <div>
          {weekDay}, {date} {timeString}
        </div>
      </h5>
    </div>
  );
}
