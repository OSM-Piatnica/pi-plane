/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  EActivityFilterType,
  ESTIMATE_SYSTEMS,
  EEstimateSystem,
  defaultActivityFilters,
  filterActivityOnSelectedFilters,
} from "@plane/constants";
import {
  MAX_WORKLOG_MINUTES,
  canViewWorklogsForRole,
  formatWorklogDuration,
  parseLoggableWorklogDuration,
  parseWorklogDuration,
} from "../../helpers/worklog";

describe("parseWorklogDuration", () => {
  it.each([
    ["90", 90],
    ["45m", 45],
    ["45 min", 45],
    ["45 mins", 45],
    ["2h", 120],
    ["2h30m", 150],
    ["2h 30m", 150],
    ["2H 30M", 150],
    ["1.5h", 90],
    ["1,5h", 90],
    ["  3h  ", 180],
  ])("reads %s as %i minutes", (input, minutes) => {
    expect(parseWorklogDuration(input)).toBe(minutes);
  });

  it.each(["", "   ", "0", "0h", "0m", "abc", "h", "m", "2x", "2h 30", "-5", "1h 1h", "2h 30m 10s"])(
    "does not read %j",
    (input) => {
      expect(parseWorklogDuration(input)).toBeNull();
    }
  );
});

describe("parseLoggableWorklogDuration", () => {
  it("accepts up to 24 hours and nothing more", () => {
    expect(parseLoggableWorklogDuration("24h")).toBe(MAX_WORKLOG_MINUTES);
    expect(parseLoggableWorklogDuration("1440")).toBe(1440);
    expect(parseLoggableWorklogDuration("24h 1m")).toBeNull();
    expect(parseLoggableWorklogDuration("1441")).toBeNull();
    expect(parseLoggableWorklogDuration("nope")).toBeNull();
  });
});

describe("formatWorklogDuration", () => {
  it.each([
    [0, "0m"],
    [1, "1m"],
    [59, "59m"],
    [60, "1h"],
    [90, "1h 30m"],
    [1440, "24h"],
    [-5, "0m"],
    [Number.NaN, "0m"],
  ])("writes %i minutes as %s", (minutes, text) => {
    expect(formatWorklogDuration(minutes)).toBe(text);
  });

  it("writes what parseWorklogDuration reads", () => {
    for (const minutes of [1, 45, 60, 61, 150, 1440]) {
      expect(parseWorklogDuration(formatWorklogDuration(minutes))).toBe(minutes);
    }
  });
});

describe("who sees the logged time", () => {
  it("is project admins and members, not guests", () => {
    expect(canViewWorklogsForRole(20)).toBe(true);
    expect(canViewWorklogsForRole(15)).toBe(true);
    expect(canViewWorklogsForRole(5)).toBe(false);
    expect(canViewWorklogsForRole(undefined)).toBe(false);
  });
});

const entry = (activity_type: string) => ({ id: activity_type, activity_type }) as never;

describe("the activity of a work item", () => {
  it("shows logged time by default, and hides it when its filter is off", () => {
    expect(defaultActivityFilters).toContain(EActivityFilterType.WORKLOG);
    const items = [entry("WORKLOG"), entry("COMMENT")];
    expect(filterActivityOnSelectedFilters(items, defaultActivityFilters)).toHaveLength(2);
    expect(filterActivityOnSelectedFilters(items, [EActivityFilterType.COMMENT])).toHaveLength(1);
  });
});

describe("the time estimate system", () => {
  it("is available, with its hours in minutes", () => {
    const time = ESTIMATE_SYSTEMS[EEstimateSystem.TIME];
    expect(time.is_available).toBe(true);
    expect(time.is_ee).toBe(false);
    expect(time.templates.hours.values.map((point) => point.value)).toEqual(["60", "120", "180", "240", "300", "360"]);
  });
});
