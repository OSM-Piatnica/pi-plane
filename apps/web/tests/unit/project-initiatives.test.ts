/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it, vi } from "vitest";
import { EUserWorkspaceRoles } from "@plane/types";
import type { TInitiative, TProject, TProjectDisplayFilters, TProjectFilters } from "@plane/types";
import {
  buildInitiativeTree,
  canReadInitiatives,
  getInitiativeIdsByGoal,
  getInitiativeOrder,
} from "@/helpers/initiatives";
import type { RootStore } from "@/store/root.store";
import { ProjectStore } from "@/store/project/project.store";

// the store builds its services in the constructor; the real ones would need the API configuration
vi.mock("@/services/project", () => {
  class FakeService {
    readonly isFake = true;
  }
  return { ProjectService: FakeService, ProjectStateService: FakeService, ProjectArchiveService: FakeService };
});
vi.mock("@/services/issue", () => {
  class FakeService {
    readonly isFake = true;
  }
  return { IssueLabelService: FakeService, IssueService: FakeService };
});

const initiative = (id: string, overrides: Partial<TInitiative> = {}) =>
  ({
    id,
    kind: "initiative",
    parent: null,
    name: id,
    sort_order: 1,
    created_at: "2026-11-01T00:00:00Z",
    ...overrides,
  }) as TInitiative;

// a goal G with initiatives A and B, and a loose initiative C
const ITEMS = [
  initiative("G", { kind: "goal", sort_order: 1 }),
  initiative("A", { parent: "G", sort_order: 1 }),
  initiative("B", { parent: "G", sort_order: 2 }),
  initiative("C", { sort_order: 3 }),
];

describe("the project list's view of the initiative tree", () => {
  const tree = buildInitiativeTree(ITEMS);

  it("orders the groups like the Initiatives app: a goal's initiatives, then the loose ones", () => {
    expect(getInitiativeOrder(tree)).toEqual(["A", "B", "C"]);
  });

  it("lets a goal stand for its initiatives", () => {
    expect(getInitiativeIdsByGoal(tree)).toEqual({ G: ["A", "B"] });
  });

  it("lets only workspace admins and members read initiatives", () => {
    expect(canReadInitiatives(EUserWorkspaceRoles.ADMIN)).toBe(true);
    expect(canReadInitiatives(EUserWorkspaceRoles.MEMBER)).toBe(true);
    expect(canReadInitiatives(EUserWorkspaceRoles.GUEST)).toBe(false);
    expect(canReadInitiatives(undefined)).toBe(false);
  });
});

const project = (id: string, initiative_ids: string[]) =>
  ({
    id,
    name: id,
    identifier: id,
    workspace: "w1",
    archived_at: null,
    created_at: id,
    initiative_ids,
  }) as unknown as TProject;

const makeStore = (filters: TProjectFilters, enabledFeatures: string[]) => {
  const displayFilters: TProjectDisplayFilters = { order_by: "name" };
  const root = {
    workspaceRoot: { currentWorkspace: { id: "w1", enabled_features: enabledFeatures } },
    projectRoot: {
      projectFilter: {
        currentWorkspaceDisplayFilters: displayFilters,
        currentWorkspaceFilters: filters,
        searchQuery: "",
      },
    },
    initiative: { tree: buildInitiativeTree(ITEMS) },
  } as unknown as RootStore;
  const store = new ProjectStore(root);
  store.projectMap = {
    p1: project("p1", ["A"]),
    p2: project("p2", ["C"]),
    p3: project("p3", []),
  };
  return store;
};

describe("ProjectStore and the initiative filter", () => {
  it("keeps the projects of a goal's initiatives", () => {
    expect(makeStore({ initiatives: ["G"] }, ["initiatives"]).filteredProjectIds).toEqual(["p1"]);
  });

  it("keeps the projects in no initiative with the keyword", () => {
    expect(makeStore({ initiatives: ["none", "C"] }, ["initiatives"]).filteredProjectIds).toEqual(["p2", "p3"]);
  });

  it("ignores the filter while the feature is off", () => {
    expect(makeStore({ initiatives: ["G"] }, []).filteredProjectIds).toEqual(["p1", "p2", "p3"]);
  });

  it("follows links and unlinks made in the Initiatives app", () => {
    const store = makeStore({}, ["initiatives"]);

    store.updateProjectInitiativeLinks(["p1", "p3"], "C", true);
    expect(store.projectMap.p1.initiative_ids).toEqual(["A", "C"]);
    expect(store.projectMap.p3.initiative_ids).toEqual(["C"]);

    store.updateProjectInitiativeLinks(["p1"], "A", false);
    expect(store.projectMap.p1.initiative_ids).toEqual(["C"]);
  });
});
