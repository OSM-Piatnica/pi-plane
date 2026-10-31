/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  buildTemplateGroupsPayload,
  getAddableTemplateGroups,
  getGroupPaths,
  mapTemplateGroupsFromPayload,
} from "@/helpers/project-template-groups";

const group = (id: string, name: string, parent: string | null = null) => ({ id, name, parent });
const groups = [group("a", "Plant"), group("b", "Night shift", "a"), group("c", "Office")];

describe("getGroupPaths", () => {
  it("writes nested groups as Parent / Child", () => {
    const paths = getGroupPaths(groups);
    expect(paths.get("a")).toBe("Plant");
    expect(paths.get("b")).toBe("Plant / Night shift");
  });
  it("stops on a cycle instead of looping", () => {
    const paths = getGroupPaths([group("x", "X", "y"), group("y", "Y", "x")]);
    expect(paths.get("x")).toBe("Y / X");
  });
});

describe("mapTemplateGroupsFromPayload", () => {
  it("keeps entries with an id and a valid role", () => {
    expect(
      mapTemplateGroupsFromPayload([
        { group: "a", path: "Plant", role: 15 },
        { path: "No id", role: 15 },
        { group: "z", role: 20 as unknown as 15 },
      ])
    ).toEqual([{ group: "a", path: "Plant", role: 15 }]);
  });
  it("is empty without groups", () => {
    expect(mapTemplateGroupsFromPayload(undefined)).toEqual([]);
  });
});

describe("buildTemplateGroupsPayload", () => {
  it("writes the current path next to the id, so the file can be uploaded elsewhere", () => {
    const rows = [{ group: "b", path: "old name", role: 5 as const }];
    expect(buildTemplateGroupsPayload(rows, getGroupPaths(groups))).toEqual([
      { group: "b", path: "Plant / Night shift", role: 5 },
    ]);
  });
  it("keeps the stored path of a group that no longer exists and drops duplicates", () => {
    const rows = [
      { group: "gone", path: "Old / Group", role: 15 as const },
      { group: "gone", path: "Old / Group", role: 5 as const },
    ];
    expect(buildTemplateGroupsPayload(rows, getGroupPaths(groups))).toEqual([
      { group: "gone", path: "Old / Group", role: 15 },
    ]);
  });
});

describe("getAddableTemplateGroups", () => {
  it("lists the groups not yet in the template, by path", () => {
    expect(getAddableTemplateGroups(groups, [{ group: "a" }])).toEqual([
      { id: "c", path: "Office" },
      { id: "b", path: "Plant / Night shift" },
    ]);
  });
});
