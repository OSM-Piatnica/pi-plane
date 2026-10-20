/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  ALL_EPICS_GROUP_NAME,
  ALL_ISSUES_GROUP_ID,
  COMPLETED_CYCLE_DROP_ERROR,
  getGroupColumnName,
} from "../../helpers/group-column";

const t = (key: string) => `[${key}]`;

describe("getGroupColumnName", () => {
  it("translates the empty 'None' group by its id", () => {
    expect(getGroupColumnName({ id: "None", name: "None" }, t)).toBe("[common.none]");
  });

  it("translates the 'All' group of an ungrouped layout, for work items and for epics", () => {
    expect(getGroupColumnName({ id: ALL_ISSUES_GROUP_ID, name: "All work items" }, t)).toBe(
      "[default_global_view.all_issues]"
    );
    expect(getGroupColumnName({ id: ALL_ISSUES_GROUP_ID, name: ALL_EPICS_GROUP_NAME }, t)).toBe("[epic.all]");
  });

  it("keeps the name of every other group, such as a user's own cycle called None-ish", () => {
    expect(getGroupColumnName({ id: "abc", name: "None" }, t)).toBe("None");
    expect(getGroupColumnName({ id: "state-1", name: "In progress" }, t)).toBe("In progress");
  });
});

describe("COMPLETED_CYCLE_DROP_ERROR", () => {
  it("is a marker, not display text", () => {
    expect(COMPLETED_CYCLE_DROP_ERROR).not.toMatch(/\s/);
  });
});
