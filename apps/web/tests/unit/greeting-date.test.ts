/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { formatGreetingDate, getGreetingPeriod } from "@/helpers/greeting-date";

const monday = new Date("2026-10-19T14:05:00Z");

describe("formatGreetingDate", () => {
  it("keeps the English text the home page always showed", () => {
    expect(formatGreetingDate("en-US", monday, "UTC")).toEqual({
      weekDay: "Monday",
      date: "Oct 19",
      time: "14:05",
      hour: 14,
    });
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

  it("gives the hour in the user's time zone, so the greeting agrees with the clock", () => {
    // 16:30 UTC is 18:30 in Warsaw and 12:30 in New York
    const instant = new Date("2026-10-20T16:30:00Z");
    expect(formatGreetingDate("en-US", instant, "Europe/Warsaw").hour).toBe(18);
    expect(formatGreetingDate("en-US", instant, "America/New_York").hour).toBe(12);
    expect(formatGreetingDate("en-US", new Date("2026-10-19T22:30:00Z"), "Europe/Warsaw").hour).toBe(0);
  });

  it("reads the weekday and the date in the user's time zone too", () => {
    // 01:30 UTC on Wednesday is still Tuesday evening in New York
    const instant = new Date("2026-10-21T01:30:00Z");
    expect(formatGreetingDate("en-US", instant, "Europe/Warsaw")).toMatchObject({
      weekDay: "Wednesday",
      date: "Oct 21",
    });
    expect(formatGreetingDate("en-US", instant, "America/New_York")).toMatchObject({
      weekDay: "Tuesday",
      date: "Oct 20",
    });
  });

  it("falls back to the browser's time zone for an empty or unknown one instead of throwing", () => {
    expect(() => formatGreetingDate("en-US", monday, "")).not.toThrow();
    expect(() => formatGreetingDate("en-US", monday, null)).not.toThrow();
    expect(() => formatGreetingDate("en-US", monday, "Not/AZone")).not.toThrow();
    expect(formatGreetingDate("en-US", monday, "").time).toBe(formatGreetingDate("en-US", monday, undefined).time);
  });
});

describe("getGreetingPeriod", () => {
  it("splits the day into morning, afternoon and evening", () => {
    expect([0, 11].map(getGreetingPeriod)).toEqual(["morning", "morning"]);
    expect([12, 17].map(getGreetingPeriod)).toEqual(["afternoon", "afternoon"]);
    expect([18, 23].map(getGreetingPeriod)).toEqual(["evening", "evening"]);
  });
});
