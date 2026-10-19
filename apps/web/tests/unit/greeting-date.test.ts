/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { formatGreetingDate } from "@/helpers/greeting-date";

const monday = new Date("2026-10-19T14:05:00Z");

describe("formatGreetingDate", () => {
  it("keeps the English text the home page always showed", () => {
    expect(formatGreetingDate("en-US", monday, "UTC")).toEqual({ weekDay: "Monday", date: "Oct 19", time: "14:05" });
  });

  it("uses the user's language for the weekday and the date", () => {
    const pl = formatGreetingDate("pl", monday, "UTC");
    expect(pl.weekDay).toBe("poniedziałek");
    expect(pl.date).toMatch(/19/);
    expect(pl.date).not.toMatch(/Oct/);
    expect(formatGreetingDate("de", monday, "UTC").weekDay).toBe("Montag");
  });

  it("shows the clock in the user's time zone on a 24-hour clock, with no 24:xx at midnight", () => {
    expect(formatGreetingDate("en-US", monday, "Europe/Warsaw").time).toBe("16:05");
    expect(formatGreetingDate("en-US", new Date("2026-10-19T22:30:00Z"), "Europe/Warsaw").time).toBe("00:30");
  });
});
