/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getDateBucket, getDateBucketDropDate, isDateBucketGroupBy } from "../src/date-bucket";

const MONDAY = 1;
const SUNDAY = 0;

// 2026-03-04 is a Wednesday
const wednesday = new Date(2026, 2, 4, 15, 30);

describe("getDateBucket", () => {
  it("puts days into the buckets of a Monday to Sunday week", () => {
    expect(getDateBucket("2026-03-03", wednesday, MONDAY)).toBe("earlier");
    expect(getDateBucket("2026-03-04", wednesday, MONDAY)).toBe("today");
    expect(getDateBucket("2026-03-05", wednesday, MONDAY)).toBe("this_week");
    expect(getDateBucket("2026-03-08", wednesday, MONDAY)).toBe("this_week");
    expect(getDateBucket("2026-03-09", wednesday, MONDAY)).toBe("next_week");
    expect(getDateBucket("2026-03-15", wednesday, MONDAY)).toBe("next_week");
    expect(getDateBucket("2026-03-16", wednesday, MONDAY)).toBe("later");
  });

  it("is none without a date", () => {
    expect(getDateBucket(null, wednesday, MONDAY)).toBe("no_date");
    expect(getDateBucket(undefined, wednesday, MONDAY)).toBe("no_date");
    expect(getDateBucket("", wednesday, MONDAY)).toBe("no_date");
  });

  it("reads the day of a timestamp", () => {
    expect(getDateBucket("2026-03-04T23:59:00Z", wednesday, MONDAY)).toBe("today");
  });

  it("starts next week on Monday when today is Sunday", () => {
    const sunday = new Date(2026, 2, 8);
    expect(getDateBucket("2026-03-09", sunday, MONDAY)).toBe("next_week");
    expect(getDateBucket("2026-03-08", sunday, MONDAY)).toBe("today");
  });
});

describe("getDateBucketDropDate", () => {
  it("gives a day for today and the weeks, nothing for no_date and no day for earlier and later", () => {
    expect(getDateBucketDropDate("today", wednesday, { weekStart: MONDAY })).toBe("2026-03-04");
    expect(getDateBucketDropDate("this_week", wednesday, { weekStart: MONDAY })).toBe("2026-03-08");
    expect(getDateBucketDropDate("next_week", wednesday, { weekStart: MONDAY })).toBe("2026-03-15");
    expect(getDateBucketDropDate("no_date", wednesday, { weekStart: MONDAY })).toBeNull();
    expect(getDateBucketDropDate("earlier", wednesday, { weekStart: MONDAY })).toBeUndefined();
    expect(getDateBucketDropDate("later", wednesday, { weekStart: MONDAY })).toBeUndefined();
  });

  it("lands in the bucket it was dropped on", () => {
    for (const bucket of ["today", "this_week", "next_week"] as const) {
      expect(getDateBucket(getDateBucketDropDate(bucket, wednesday) as string, wednesday)).toBe(bucket);
    }
  });
});

describe("the day in a time zone", () => {
  it("takes the current day as a yyyy-mm-dd string", () => {
    expect(getDateBucket("2026-03-04", "2026-03-04", MONDAY)).toBe("today");
    expect(getDateBucket("2026-03-04", "2026-03-05", MONDAY)).toBe("earlier");
    expect(getDateBucketDropDate("next_week", "2026-03-04", { weekStart: MONDAY })).toBe("2026-03-15");
  });
});

describe("a Sunday", () => {
  it("has no day left in this week to drop on", () => {
    expect(getDateBucketDropDate("this_week", "2026-03-08", { weekStart: MONDAY })).toBeUndefined();
    expect(getDateBucketDropDate("this_week", "2026-03-07", { weekStart: MONDAY })).toBe("2026-03-08");
    expect(getDateBucketDropDate("next_week", "2026-03-08", { weekStart: MONDAY })).toBe("2026-03-15");
  });
});

describe("isDateBucketGroupBy", () => {
  it("knows the three date bucket group bys", () => {
    for (const key of ["start_date_bucket", "target_date_bucket", "finish_date_bucket"]) {
      expect(isDateBucketGroupBy(key)).toBe(true);
    }
    expect(isDateBucketGroupBy("target_date")).toBe(false);
    expect(isDateBucketGroupBy(null)).toBe(false);
  });
});

describe("working days", () => {
  // 2026-03-04 is a Wednesday; weekend days are numbered like Date.getDay(), 0 = Sunday
  const monToFri = [0, 6];
  const monToThu = [5, 6, 0]; // Friday off as well
  const sunToThu = [5, 6]; // a Sunday to Thursday working week

  it("drops a finish or due date on the last working day of the week, a start date on the first", () => {
    expect(getDateBucketDropDate("this_week", "2026-03-04", { weekStart: MONDAY, weekendDays: monToFri })).toBe(
      "2026-03-06"
    );
    expect(
      getDateBucketDropDate("this_week", "2026-03-04", { weekStart: MONDAY, weekendDays: monToFri, edge: "start" })
    ).toBe("2026-03-05");
    expect(getDateBucketDropDate("next_week", "2026-03-04", { weekStart: MONDAY, weekendDays: monToFri })).toBe(
      "2026-03-13"
    );
    expect(
      getDateBucketDropDate("next_week", "2026-03-04", { weekStart: MONDAY, weekendDays: monToFri, edge: "start" })
    ).toBe("2026-03-09");
    expect(getDateBucketDropDate("this_week", "2026-03-04", { weekStart: MONDAY, weekendDays: monToThu })).toBe(
      "2026-03-05"
    );
  });

  it("has no day left in this week once only weekend days remain", () => {
    // Friday 2026-03-06, Saturday and Sunday off
    expect(
      getDateBucketDropDate("this_week", "2026-03-06", { weekStart: MONDAY, weekendDays: monToFri })
    ).toBeUndefined();
    // Saturday
    expect(
      getDateBucketDropDate("this_week", "2026-03-07", { weekStart: MONDAY, weekendDays: monToFri })
    ).toBeUndefined();
    // Thursday, Friday and Saturday off: after Wednesday only the Sunday... Monday-based week ends on Sunday (working)
    expect(getDateBucketDropDate("this_week", "2026-03-05", { weekStart: MONDAY, weekendDays: sunToThu })).toBe(
      "2026-03-08"
    );
  });

  it("keeps today and no date as they are", () => {
    expect(getDateBucketDropDate("today", "2026-03-07", { weekStart: MONDAY, weekendDays: monToFri })).toBe(
      "2026-03-07"
    );
    expect(getDateBucketDropDate("no_date", "2026-03-07", { weekStart: MONDAY, weekendDays: monToFri })).toBeNull();
  });
});

describe("the start of the week", () => {
  it("counts a week from Sunday by default, like a project and a workspace", () => {
    // Wednesday 2026-03-04: the week ends on Saturday the 7th
    expect(getDateBucket("2026-03-07", "2026-03-04")).toBe("this_week");
    expect(getDateBucket("2026-03-08", "2026-03-04")).toBe("next_week");
    expect(getDateBucket("2026-03-15", "2026-03-04")).toBe("later");
  });

  it("follows the week of the project", () => {
    expect(getDateBucket("2026-03-08", "2026-03-04", MONDAY)).toBe("this_week");
    expect(getDateBucket("2026-03-08", "2026-03-04", SUNDAY)).toBe("next_week");
    // a week that starts on Saturday ends on Friday
    expect(getDateBucket("2026-03-06", "2026-03-04", 6)).toBe("this_week");
    expect(getDateBucket("2026-03-07", "2026-03-04", 6)).toBe("next_week");
  });

  it("drops on a working day of the week of the project", () => {
    const weekendDays = [0, 6];
    expect(getDateBucketDropDate("this_week", "2026-03-04", { weekendDays, weekStart: SUNDAY })).toBe("2026-03-06");
    expect(getDateBucketDropDate("next_week", "2026-03-04", { weekendDays, weekStart: SUNDAY })).toBe("2026-03-13");
    // a Saturday is the last day of a Sunday week: nothing is left of it
    expect(getDateBucketDropDate("this_week", "2026-03-07", { weekendDays, weekStart: SUNDAY })).toBeUndefined();
  });
});
