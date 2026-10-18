/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { COMPLETED_CYCLE_DROP_ERROR, getGroupColumnName } from "../../helpers/group-column";

const t = (key: string) => `[${key}]`;

describe("getGroupColumnName", () => {
  it("translates the empty 'None' group by its id", () => {
    expect(getGroupColumnName({ id: "None", name: "None" }, t)).toBe("[common.none]");
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
