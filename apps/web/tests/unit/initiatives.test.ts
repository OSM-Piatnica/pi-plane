/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it, vi } from "vitest";
import { EUserPermissions } from "@plane/constants";
import { EUserWorkspaceRoles } from "@plane/types";
import type { TInitiative, TInitiativeEpic, TInitiativeUpdate } from "@plane/types";
import {
  buildInitiativeTree,
  canDeleteInitiative,
  canLinkInProject,
  getInitiativeErrorMessage,
  getInitiativeProgressPercentage,
} from "@/helpers/initiatives";
import { InitiativeStore } from "@/store/initiative.store";

// the store is always given a fake service here; the real one would need the API configuration
vi.mock("@/services/initiative.service", () => ({
  InitiativeService: class {
    list = vi.fn();
  },
}));

const translate = (key: string) => `t:${key}`;

const progress = (completed = 0, total = 0, cancelled = 0) => ({
  total_issues: total,
  backlog: 0,
  unstarted: 0,
  started: total - completed - cancelled,
  completed,
  cancelled,
});

const make = (id: string, overrides: Partial<TInitiative> = {}): TInitiative => ({
  id,
  workspace: "w1",
  kind: "initiative",
  parent: null,
  name: id,
  description: "",
  description_html: "<p></p>",
  lead: null,
  start_date: null,
  target_date: null,
  status: "planned",
  health: null,
  logo_props: {},
  color: "",
  sort_order: 1,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
  created_by: "creator",
  progress: progress(),
  progress_is_partial: false,
  hidden_project_count: 0,
  project_ids: [],
  epic_ids: [],
  hidden_epic_count: 0,
  initiative_ids: [],
  epic_progress: progress(),
  epic_progress_is_partial: false,
  ...overrides,
});

describe("getInitiativeProgressPercentage", () => {
  it("counts completed and cancelled work items as done, rounded down", () => {
    expect(getInitiativeProgressPercentage(progress(1, 3))).toBe(33);
    expect(getInitiativeProgressPercentage(progress(1, 4, 1))).toBe(50);
    expect(getInitiativeProgressPercentage(progress(2, 2))).toBe(100);
  });

  it("is zero without work items", () => {
    expect(getInitiativeProgressPercentage(progress())).toBe(0);
    expect(getInitiativeProgressPercentage(undefined)).toBe(0);
  });
});

describe("buildInitiativeTree", () => {
  it("puts each goal before its initiatives, in list order, and the others last", () => {
    const tree = buildInitiativeTree([
      make("loose"),
      make("g2", { kind: "goal", sort_order: 2 }),
      make("g1", { kind: "goal", sort_order: 1 }),
      make("b", { parent: "g1", sort_order: 2 }),
      make("a", { parent: "g1", sort_order: 1 }),
      make("c", { parent: "g2" }),
      make("orphan", { parent: "deleted-goal" }),
    ]);

    expect(tree.map((node) => [node.goal?.id, node.initiatives.map((item) => item.id)])).toEqual([
      ["g1", ["a", "b"]],
      ["g2", ["c"]],
      [undefined, ["loose", "orphan"]],
    ]);
  });

  it("has no group without a goal when every initiative has one", () => {
    const tree = buildInitiativeTree([make("g", { kind: "goal" }), make("a", { parent: "g" })]);
    expect(tree).toHaveLength(1);
    expect(buildInitiativeTree([])).toEqual([]);
  });
});

describe("canDeleteInitiative", () => {
  const initiative = { lead: "lead", created_by: "creator" };

  it("lets a workspace admin, the lead and the creator delete", () => {
    expect(canDeleteInitiative(initiative, "someone", EUserWorkspaceRoles.ADMIN)).toBe(true);
    expect(canDeleteInitiative(initiative, "lead", EUserWorkspaceRoles.MEMBER)).toBe(true);
    expect(canDeleteInitiative(initiative, "creator", EUserWorkspaceRoles.MEMBER)).toBe(true);
  });

  it("refuses another member, a guest and an unknown person", () => {
    expect(canDeleteInitiative(initiative, "someone", EUserWorkspaceRoles.MEMBER)).toBe(false);
    expect(canDeleteInitiative(initiative, "lead", EUserWorkspaceRoles.GUEST)).toBe(false);
    expect(canDeleteInitiative(initiative, undefined, EUserWorkspaceRoles.MEMBER)).toBe(false);
    expect(canDeleteInitiative(initiative, "lead", undefined)).toBe(false);
  });
});

describe("canLinkInProject", () => {
  it("follows the API: a workspace admin always, others with the Member role in the project", () => {
    expect(canLinkInProject(EUserWorkspaceRoles.ADMIN, undefined)).toBe(true);
    expect(canLinkInProject(EUserWorkspaceRoles.MEMBER, EUserPermissions.MEMBER)).toBe(true);
    expect(canLinkInProject(EUserWorkspaceRoles.MEMBER, EUserPermissions.ADMIN)).toBe(true);
    expect(canLinkInProject(EUserWorkspaceRoles.MEMBER, EUserPermissions.GUEST)).toBe(false);
    expect(canLinkInProject(EUserWorkspaceRoles.MEMBER, undefined)).toBe(false);
  });
});

describe("getInitiativeErrorMessage", () => {
  it("uses the message the API gives", () => {
    expect(getInitiativeErrorMessage({ error: "Not allowed." }, translate)).toBe("Not allowed.");
    expect(
      getInitiativeErrorMessage({ target_date: ["The target date cannot be before the start date."] }, translate)
    ).toBe("The target date cannot be before the start date.");
  });

  it("falls back to the general message", () => {
    expect(getInitiativeErrorMessage(undefined, translate)).toBe("t:initiatives.toast.error");
    expect(getInitiativeErrorMessage({ detail: 3 }, translate)).toBe("t:initiatives.toast.error");
  });
});

const service = () => ({
  list: vi.fn(),
  retrieve: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  remove: vi.fn(),
  linkProjects: vi.fn(),
  unlinkProject: vi.fn(),
  listEpics: vi.fn(),
  searchEpics: vi.fn(),
  linkEpics: vi.fn(),
  unlinkEpic: vi.fn(),
  listUpdates: vi.fn(),
  createUpdate: vi.fn(),
});

describe("InitiativeStore", () => {
  it("loads the list of a workspace and starts over for another one", async () => {
    const api = service();
    api.list.mockResolvedValueOnce([make("a"), make("g", { kind: "goal" })]).mockResolvedValueOnce([make("x")]);
    const store = new InitiativeStore(api);

    await store.fetchInitiatives("acme");
    expect(store.isListLoaded).toBe(true);
    expect(store.goals.map((goal) => goal.id)).toEqual(["g"]);
    expect(store.getInitiativeById("a")?.name).toBe("a");

    await store.fetchInitiatives("other");
    expect(Object.keys(store.initiativeMap)).toEqual(["x"]);
  });

  it("changes a field at once and puts it back when the request fails", async () => {
    const api = service();
    api.list.mockResolvedValue([make("a")]);
    let reject!: (reason: unknown) => void;
    api.update.mockReturnValue(
      new Promise((_, fail) => {
        reject = fail;
      })
    );
    const store = new InitiativeStore(api);
    await store.fetchInitiatives("acme");

    const pending = store.updateInitiative("acme", "a", { status: "active" });
    expect(store.getInitiativeById("a")?.status).toBe("active");
    reject({ error: "No." });
    await expect(pending).rejects.toEqual({ error: "No." });
    expect(store.getInitiativeById("a")?.status).toBe("planned");
  });

  it("refreshes the old and the new goal when an initiative moves", async () => {
    const api = service();
    api.list.mockResolvedValue([
      make("g1", { kind: "goal" }),
      make("g2", { kind: "goal" }),
      make("a", { parent: "g1" }),
    ]);
    api.update.mockResolvedValue(make("a", { parent: "g2" }));
    api.retrieve.mockImplementation((_slug: string, id: string) =>
      Promise.resolve(make(id, { kind: "goal", name: `${id} fresh` }))
    );
    const store = new InitiativeStore(api);
    await store.fetchInitiatives("acme");

    await store.updateInitiative("acme", "a", { parent: "g2" });

    expect(api.retrieve.mock.calls.map((call) => call[1])).toEqual(["g1", "g2"]);
    expect(store.getInitiativeById("g1")?.name).toBe("g1 fresh");
    expect(store.tree.find((node) => node.goal?.id === "g2")?.initiatives.map((item) => item.id)).toEqual(["a"]);
  });

  it("keeps the initiatives of a deleted goal, without a goal", async () => {
    const api = service();
    api.list.mockResolvedValue([make("g", { kind: "goal" }), make("a", { parent: "g" })]);
    api.remove.mockResolvedValue(undefined);
    const store = new InitiativeStore(api);
    await store.fetchInitiatives("acme");

    await store.deleteInitiative("acme", "g");

    expect(store.getInitiativeById("g")).toBeUndefined();
    expect(store.getInitiativeById("a")?.parent).toBeNull();
  });

  it("takes the answer of a link and refreshes the goal and the Epics", async () => {
    const api = service();
    api.list.mockResolvedValue([make("g", { kind: "goal" }), make("a", { parent: "g" })]);
    api.linkEpics.mockResolvedValue(make("a", { parent: "g", epic_ids: ["e1"] }));
    const epic = { id: "e1", name: "Epic" } as TInitiativeEpic;
    api.listEpics.mockResolvedValue([epic]);
    api.retrieve.mockResolvedValue(make("g", { kind: "goal", epic_ids: ["e1"] }));
    const store = new InitiativeStore(api);
    await store.fetchInitiatives("acme");

    await store.linkEpics("acme", "a", ["e1"]);

    expect(store.getInitiativeById("a")?.epic_ids).toEqual(["e1"]);
    expect(store.epicsMap.a).toEqual([epic]);
    expect(store.getInitiativeById("g")?.epic_ids).toEqual(["e1"]);
  });

  it("removes an unlinked Epic and fetches the initiative again", async () => {
    const api = service();
    api.list.mockResolvedValue([make("a", { epic_ids: ["e1", "e2"] })]);
    api.listEpics.mockResolvedValue([{ id: "e1" }, { id: "e2" }] as TInitiativeEpic[]);
    api.unlinkEpic.mockResolvedValue(undefined);
    api.retrieve.mockResolvedValue(make("a", { epic_ids: ["e2"] }));
    const store = new InitiativeStore(api);
    await store.fetchInitiatives("acme");
    await store.fetchEpics("acme", "a");

    await store.unlinkEpic("acme", "a", "e1");

    expect(store.epicsMap.a.map((epic) => epic.id)).toEqual(["e2"]);
    expect(store.getInitiativeById("a")?.epic_ids).toEqual(["e2"]);
  });

  it("puts a new status update first and takes its health", async () => {
    const api = service();
    api.list.mockResolvedValue([make("a")]);
    const older = { id: "u1", health: "on_track" } as TInitiativeUpdate;
    const newer = { id: "u2", health: "at_risk" } as TInitiativeUpdate;
    api.listUpdates.mockResolvedValue([older]);
    api.createUpdate.mockResolvedValue(newer);
    const store = new InitiativeStore(api);
    await store.fetchInitiatives("acme");
    await store.fetchUpdates("acme", "a");

    await store.createUpdate("acme", "a", { health: "at_risk", text: "Late" });

    expect(store.updatesMap.a.map((update) => update.id)).toEqual(["u2", "u1"]);
    expect(store.getInitiativeById("a")?.health).toBe("at_risk");
  });
});
