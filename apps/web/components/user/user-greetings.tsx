/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane types
import { useTranslation } from "@plane/i18n";
// hooks
import type { IUser } from "@plane/types";
import { useCurrentTime } from "@/hooks/use-current-time";
// types

export interface IUserGreetingsView {
  user: IUser;
}

const HOUR_FORMATTER = new Intl.DateTimeFormat("en-US", {
  hour12: false,
  hour: "numeric",
});

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

const WEEKDAY_FORMATTER = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
});

const timeFormatters = new Map<string | undefined, Intl.DateTimeFormat>();

const getTimeFormatter = (timeZone: string | undefined) => {
  let formatter = timeFormatters.get(timeZone);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat("en-US", {
      timeZone,
      hour12: false, // Use 24-hour format
      hour: "2-digit",
      minute: "2-digit",
    });
    timeFormatters.set(timeZone, formatter);
  }
  return formatter;
};

export function UserGreetingsView(props: IUserGreetingsView) {
  const { user } = props;
  // current time hook
  const { currentTime } = useCurrentTime();
  // store hooks
  const { t } = useTranslation();

  const hour = HOUR_FORMATTER.format(currentTime);
  const date = DATE_FORMATTER.format(currentTime);
  const weekDay = WEEKDAY_FORMATTER.format(currentTime);
  const timeString = getTimeFormatter(user?.user_timezone).format(currentTime);

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
