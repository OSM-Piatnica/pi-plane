/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { ISSUE_EXPORT_FIELD_GROUPS, ISSUE_EXPORT_REQUIRED_FIELDS } from "@plane/constants";
import type { TOptionGroup } from "../../helpers/option-groups";
import { getGroupSelectionState, getOptionKeys, toggleGroup, toggleOption } from "../../helpers/option-groups";

const quoted = (text: string) => [...text.matchAll(/"([a-z_]+)"/g)].map((match) => match[1]);

const group = (key: string, ...options: string[]): TOptionGroup => ({
  key,
  label: key,
  options: options.map((option) => ({ key: option, label: option })),
});

describe("option groups", () => {
  const people = group("people", "assignees", "subscribers");
  const dates = group("dates", "start_date", "target_date");

  it("reports whether a group is fully, partly or not selected", () => {
    expect(getGroupSelectionState(people, [])).toBe("none");
    expect(getGroupSelectionState(people, ["assignees", "labels"])).toBe("some");
    expect(getGroupSelectionState(people, ["subscribers", "assignees"])).toBe("all");
  });

  it("selects the whole group when it is not fully selected, keeping the rest", () => {
    expect(toggleGroup(people, ["start_date"]).toSorted()).toEqual(["assignees", "start_date", "subscribers"]);
    expect(toggleGroup(people, ["assignees"]).toSorted()).toEqual(["assignees", "subscribers"]);
  });

  it("clears the whole group when it is fully selected, keeping the rest", () => {
    expect(toggleGroup(people, ["assignees", "subscribers", "start_date"])).toEqual(["start_date"]);
  });

  it("toggles a single option", () => {
    expect(toggleOption("assignees", ["labels"])).toEqual(["labels", "assignees"]);
    expect(toggleOption("assignees", ["labels", "assignees"])).toEqual(["labels"]);
  });

  it("lists every option key in order", () => {
    expect(getOptionKeys([people, dates])).toEqual(["assignees", "subscribers", "start_date", "target_date"]);
  });
});

describe("export columns of the API", () => {
  // The picker lists these columns, so one the web app does not know cannot be switched off and one
  // it invents would be refused by the API.
  const source = readFileSync(
    resolve(import.meta.dirname, "../../../../apps/api/plane/utils/porters/serializers/issue.py"),
    "utf8"
  );

  it("are grouped the same way here as in the API", () => {
    const apiGroups = source.split("ISSUE_EXPORT_FIELD_GROUPS = {")[1].split("\n}\n")[0];
    const parsed = Object.fromEntries(
      [...apiGroups.matchAll(/"([a-z_]+)": \(([^)]*)\)/g)].map((match) => [match[1], quoted(match[2])])
    );

    expect(parsed).toEqual(ISSUE_EXPORT_FIELD_GROUPS);
  });

  it("require the same columns here as in the API", () => {
    const required = source.split("ISSUE_EXPORT_REQUIRED_FIELDS = (")[1].split(")")[0];

    expect(quoted(required)).toEqual([...ISSUE_EXPORT_REQUIRED_FIELDS]);
  });
});
