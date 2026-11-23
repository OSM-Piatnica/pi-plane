/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TIssue } from "@plane/types";
import { getGroupDropValue, withEpicDropParent } from "@/helpers/group-drop";

// 2026-03-04 is a Wednesday, 2026-03-08 a Sunday
describe("getGroupDropValue", () => {
  it("moves a list property from the source group to the destination group", () => {
    expect(getGroupDropValue("labels", ["a", "b"], "a", "c")).toEqual(["b", "c"]);
    expect(getGroupDropValue("labels", ["a", "b"], "a", "None")).toEqual(["b"]);
  });

  it("sets or clears a single value", () => {
    expect(getGroupDropValue("priority", "low", "low", "high")).toBe("high");
    expect(getGroupDropValue("priority", "low", "low", "None")).toBeNull();
  });

  it("gives a dropped work item the day that stands for a time bucket, as a group and as a sub group", () => {
    expect(getGroupDropValue("target_date_bucket", "2026-01-01", "earlier", "today", "2026-03-04", [], 1)).toBe(
      "2026-03-04"
    );
    expect(getGroupDropValue("finish_date_bucket", null, "no_date", "next_week", "2026-03-04", [], 1)).toBe(
      "2026-03-15"
    );
    expect(
      getGroupDropValue("start_date_bucket", "2026-03-10", "next_week", "no_date", "2026-03-04", [], 1)
    ).toBeNull();
  });

  it("refuses a bucket that names no single day", () => {
    expect(
      getGroupDropValue("target_date_bucket", "2026-03-04", "today", "earlier", "2026-03-04", [], 1)
    ).toBeUndefined();
    expect(
      getGroupDropValue("target_date_bucket", "2026-03-04", "today", "later", "2026-03-04", [], 1)
    ).toBeUndefined();
  });

  it("refuses This week on the last day of the week", () => {
    expect(getGroupDropValue("target_date_bucket", null, "no_date", "this_week", "2026-03-08", [], 1)).toBeUndefined();
    expect(getGroupDropValue("target_date_bucket", null, "no_date", "this_week", "2026-03-07", [], 1)).toBe(
      "2026-03-08"
    );
  });
});

describe("getGroupDropValue with working days", () => {
  // 2026-03-04 is a Wednesday; weekend days are numbered like Date.getDay() (0 = Sunday)
  const weekend = [0, 6];

  it("drops a finish or due date on the last working day and a start date on the first one", () => {
    expect(getGroupDropValue("finish_date_bucket", null, "no_date", "this_week", "2026-03-04", weekend, 1)).toBe(
      "2026-03-06"
    );
    expect(getGroupDropValue("target_date_bucket", null, "no_date", "next_week", "2026-03-04", weekend, 1)).toBe(
      "2026-03-13"
    );
    expect(getGroupDropValue("start_date_bucket", null, "no_date", "this_week", "2026-03-04", weekend, 1)).toBe(
      "2026-03-05"
    );
    expect(getGroupDropValue("start_date_bucket", null, "no_date", "next_week", "2026-03-04", weekend, 1)).toBe(
      "2026-03-09"
    );
  });

  it("refuses This week on a Friday when the weekend is off", () => {
    expect(
      getGroupDropValue("finish_date_bucket", null, "no_date", "this_week", "2026-03-06", weekend, 1)
    ).toBeUndefined();
  });
});

describe("getGroupDropValue with the week of the project", () => {
  it("drops on a working day of a week that starts on Sunday", () => {
    // Saturday 2026-03-07 is the last day of that week: nothing is left of it
    expect(
      getGroupDropValue("finish_date_bucket", null, "no_date", "this_week", "2026-03-07", [0, 6], 0)
    ).toBeUndefined();
    expect(getGroupDropValue("finish_date_bucket", null, "no_date", "this_week", "2026-03-04", [0, 6], 0)).toBe(
      "2026-03-06"
    );
  });
});

describe("grouping by the hierarchy", () => {
  it("drops a work item into a parent group as that parent, and out of it as no parent", () => {
    expect(getGroupDropValue("parent", "old-parent", "old-parent", "new-parent")).toBe("new-parent");
    expect(getGroupDropValue("parent", "old-parent", "old-parent", "None")).toBeNull();
  });

  it("drops a work item into an Epic group as that Epic, and into None as no Epic", () => {
    expect(getGroupDropValue("epic", "epic-a", "epic-a", "epic-b")).toBe("epic-b");
    expect(getGroupDropValue("epic", "epic-a", "epic-a", "None")).toBeNull();
  });
});

describe("withEpicDropParent", () => {
  it("turns the Epic of a drop into the parent", () => {
    expect(withEpicDropParent({ id: "task", epic_id: "epic-b" })).toEqual({
      id: "task",
      epic_id: "epic-b",
      parent_id: "epic-b",
    });
  });

  it("drops out of every Epic into no parent", () => {
    expect(withEpicDropParent<Partial<TIssue>>({ id: "task", epic_id: null }).parent_id).toBeNull();
  });

  it("leaves any other drop alone", () => {
    const update = { id: "task", parent_id: "parent-b" };
    expect(withEpicDropParent(update)).toBe(update);
    expect(withEpicDropParent({ id: "task", priority: "high" } as const)).toEqual({ id: "task", priority: "high" });
  });
});
