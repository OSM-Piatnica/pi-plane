/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getDateBucket, getDateBucketDropDate, isDateBucketGroupBy } from "../src/date-bucket";

// 2026-03-04 is a Wednesday
const wednesday = new Date(2026, 2, 4, 15, 30);

describe("getDateBucket", () => {
  it("puts days into the buckets of a Monday to Sunday week", () => {
    expect(getDateBucket("2026-03-03", wednesday)).toBe("earlier");
    expect(getDateBucket("2026-03-04", wednesday)).toBe("today");
    expect(getDateBucket("2026-03-05", wednesday)).toBe("this_week");
    expect(getDateBucket("2026-03-08", wednesday)).toBe("this_week");
    expect(getDateBucket("2026-03-09", wednesday)).toBe("next_week");
    expect(getDateBucket("2026-03-15", wednesday)).toBe("next_week");
    expect(getDateBucket("2026-03-16", wednesday)).toBe("later");
  });

  it("is none without a date", () => {
    expect(getDateBucket(null, wednesday)).toBe("no_date");
    expect(getDateBucket(undefined, wednesday)).toBe("no_date");
    expect(getDateBucket("", wednesday)).toBe("no_date");
  });

  it("reads the day of a timestamp", () => {
    expect(getDateBucket("2026-03-04T23:59:00Z", wednesday)).toBe("today");
  });

  it("starts next week on Monday when today is Sunday", () => {
    const sunday = new Date(2026, 2, 8);
    expect(getDateBucket("2026-03-09", sunday)).toBe("next_week");
    expect(getDateBucket("2026-03-08", sunday)).toBe("today");
  });
});

describe("getDateBucketDropDate", () => {
  it("gives a day for today and the weeks, nothing for no_date and no day for earlier and later", () => {
    expect(getDateBucketDropDate("today", wednesday)).toBe("2026-03-04");
    expect(getDateBucketDropDate("this_week", wednesday)).toBe("2026-03-08");
    expect(getDateBucketDropDate("next_week", wednesday)).toBe("2026-03-15");
    expect(getDateBucketDropDate("no_date", wednesday)).toBeNull();
    expect(getDateBucketDropDate("earlier", wednesday)).toBeUndefined();
    expect(getDateBucketDropDate("later", wednesday)).toBeUndefined();
  });

  it("lands in the bucket it was dropped on", () => {
    for (const bucket of ["today", "this_week", "next_week"] as const) {
      expect(getDateBucket(getDateBucketDropDate(bucket, wednesday) as string, wednesday)).toBe(bucket);
    }
  });
});

describe("the day in a time zone", () => {
  it("takes the current day as a yyyy-mm-dd string", () => {
    expect(getDateBucket("2026-03-04", "2026-03-04")).toBe("today");
    expect(getDateBucket("2026-03-04", "2026-03-05")).toBe("earlier");
    expect(getDateBucketDropDate("next_week", "2026-03-04")).toBe("2026-03-15");
  });
});

describe("a Sunday", () => {
  it("has no day left in this week to drop on", () => {
    expect(getDateBucketDropDate("this_week", "2026-03-08")).toBeUndefined();
    expect(getDateBucketDropDate("this_week", "2026-03-07")).toBe("2026-03-08");
    expect(getDateBucketDropDate("next_week", "2026-03-08")).toBe("2026-03-15");
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
    expect(getDateBucketDropDate("this_week", "2026-03-04", { weekendDays: monToFri })).toBe("2026-03-06");
    expect(getDateBucketDropDate("this_week", "2026-03-04", { weekendDays: monToFri, edge: "start" })).toBe(
      "2026-03-05"
    );
    expect(getDateBucketDropDate("next_week", "2026-03-04", { weekendDays: monToFri })).toBe("2026-03-13");
    expect(getDateBucketDropDate("next_week", "2026-03-04", { weekendDays: monToFri, edge: "start" })).toBe(
      "2026-03-09"
    );
    expect(getDateBucketDropDate("this_week", "2026-03-04", { weekendDays: monToThu })).toBe("2026-03-05");
  });

  it("has no day left in this week once only weekend days remain", () => {
    // Friday 2026-03-06, Saturday and Sunday off
    expect(getDateBucketDropDate("this_week", "2026-03-06", { weekendDays: monToFri })).toBeUndefined();
    // Saturday
    expect(getDateBucketDropDate("this_week", "2026-03-07", { weekendDays: monToFri })).toBeUndefined();
    // Thursday, Friday and Saturday off: after Wednesday only the Sunday... Monday-based week ends on Sunday (working)
    expect(getDateBucketDropDate("this_week", "2026-03-05", { weekendDays: sunToThu })).toBe("2026-03-08");
  });

  it("keeps today and no date as they are", () => {
    expect(getDateBucketDropDate("today", "2026-03-07", { weekendDays: monToFri })).toBe("2026-03-07");
    expect(getDateBucketDropDate("no_date", "2026-03-07", { weekendDays: monToFri })).toBeNull();
  });
});
