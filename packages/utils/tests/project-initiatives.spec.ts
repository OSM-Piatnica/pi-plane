/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TProject } from "@plane/types";
import { shouldFilterProject } from "../src/project";
import { PROJECT_NO_INITIATIVE, groupProjectsByInitiative, matchesInitiativeFilter } from "../src/project-initiatives";

describe("matchesInitiativeFilter", () => {
  it("matches everything when nothing is asked for", () => {
    expect(matchesInitiativeFilter([], ["a"])).toBe(true);
    expect(matchesInitiativeFilter(null, [])).toBe(true);
  });

  it("matches a project in any of the initiatives asked for", () => {
    expect(matchesInitiativeFilter(["a", "b"], ["b", "c"])).toBe(true);
    expect(matchesInitiativeFilter(["a"], ["b", "c"])).toBe(false);
  });

  it("matches the projects in no initiative only with the keyword", () => {
    expect(matchesInitiativeFilter([PROJECT_NO_INITIATIVE], [])).toBe(true);
    expect(matchesInitiativeFilter([PROJECT_NO_INITIATIVE], undefined)).toBe(true);
    expect(matchesInitiativeFilter([PROJECT_NO_INITIATIVE], ["a"])).toBe(false);
    expect(matchesInitiativeFilter(["a"], [])).toBe(false);
    expect(matchesInitiativeFilter(["a", PROJECT_NO_INITIATIVE], ["a"])).toBe(true);
  });

  it("lets a goal stand for its initiatives", () => {
    const byGoal = { goal: ["a", "b"] };
    expect(matchesInitiativeFilter(["goal"], ["b"], byGoal)).toBe(true);
    expect(matchesInitiativeFilter(["goal"], ["c"], byGoal)).toBe(false);
    // a goal without initiatives finds nothing, and never the projects without an initiative
    expect(matchesInitiativeFilter(["empty-goal"], [], { "empty-goal": [] })).toBe(false);
  });
});

describe("groupProjectsByInitiative", () => {
  const projects = [
    { id: "p1", initiative_ids: ["b", "a"] },
    { id: "p2", initiative_ids: [] },
    { id: "p3", initiative_ids: ["a"] },
    { id: "p4" },
  ];

  it("puts a project in each of its initiatives, in the order of the initiatives", () => {
    expect(groupProjectsByInitiative(projects, ["a", "b", "c"])).toEqual([
      { key: "a", projectIds: ["p1", "p3"] },
      { key: "b", projectIds: ["p1"] },
      { key: PROJECT_NO_INITIATIVE, projectIds: ["p2", "p4"] },
    ]);
  });

  it("gives an initiative that is not loaded its own group after the others", () => {
    expect(groupProjectsByInitiative([{ id: "p1", initiative_ids: ["x", "a"] }], ["a"])).toEqual([
      { key: "a", projectIds: ["p1"] },
      { key: "x", projectIds: ["p1"] },
    ]);
  });

  it("counts an initiative named twice once", () => {
    expect(groupProjectsByInitiative([{ id: "p1", initiative_ids: ["a", "a"] }], ["a"])).toEqual([
      { key: "a", projectIds: ["p1"] },
    ]);
  });

  it("has no group for nothing", () => {
    expect(groupProjectsByInitiative([], ["a"])).toEqual([]);
  });
});

describe("shouldFilterProject with an initiative filter", () => {
  const project = { id: "p", network: 2, initiative_ids: ["a"], archived_at: null } as unknown as TProject;

  it("keeps a project of an initiative asked for, or of its goal", () => {
    expect(shouldFilterProject(project, {}, { initiatives: ["a"] })).toBe(true);
    expect(shouldFilterProject(project, {}, { initiatives: ["g"] }, { initiativeIdsByGoal: { g: ["a"] } })).toBe(true);
  });

  it("drops a project of another initiative", () => {
    expect(shouldFilterProject(project, {}, { initiatives: ["b"] })).toBe(false);
    expect(shouldFilterProject(project, {}, { initiatives: [PROJECT_NO_INITIATIVE] })).toBe(false);
  });
});
