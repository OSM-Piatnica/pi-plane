/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TIssueRelationTypes, TScheduleAnalysis, TScheduleAnalysisItem } from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import {
  getScheduleAnalysisItem,
  getScheduleAnalysisKey,
  getScheduleAnalysisNotices,
  getScheduleAnalysisScope,
  isDependencyCritical,
  isWorkItemCritical,
} from "@/helpers/schedule-analysis.helper";
import type { RootStore } from "@/store/root.store";
import { IssuesTimeLineStore } from "@/store/timeline/issues-timeline.store";

const getScheduleAnalysis = vi.hoisted(() => vi.fn());
const storage = vi.hoisted(() => ({ values: {} as Record<string, unknown> }));

vi.mock("@/services/issue", () => ({
  IssueService: class {
    getScheduleAnalysis = getScheduleAnalysis;
  },
}));

vi.mock("@/hooks/use-local-storage", () => ({
  getValueFromLocalStorage: (key: string, defaultValue: unknown) => storage.values[key] ?? defaultValue,
  setValueIntoLocalStorage: (key: string, value: unknown) => {
    storage.values[key] = value;
    return true;
  },
}));

const item = (overrides: Partial<TScheduleAnalysisItem> = {}): TScheduleAnalysisItem => ({
  earliest_start: "2027-06-07",
  earliest_finish: "2027-06-09",
  latest_start: "2027-06-07",
  latest_finish: "2027-06-09",
  total_float: 0,
  is_critical: true,
  is_fixed: false,
  needed_by: null,
  ...overrides,
});

const analysis = (overrides: Partial<TScheduleAnalysis> = {}): TScheduleAnalysis => ({
  project_start: "2027-06-07",
  project_end: "2027-06-18",
  items: {
    a: item(),
    b: item(),
    c: item({ total_float: 3, is_critical: false, latest_finish: "2027-06-14" }),
    done: item({ total_float: null, is_critical: false, is_fixed: true }),
  },
  critical_ids: ["a", "b"],
  critical_links: [{ source: "a", target: "b", relation_type: "blocking" }],
  cycles: [],
  undated_count: 0,
  inverted_count: 0,
  undated_linked_ids: [],
  weekend_days: [0, 6],
  analysed_count: 4,
  max_items: 2000,
  truncated: false,
  ...overrides,
});

/** A request that stays open until `resolve` is called. */
const deferred = () => {
  const handle = {} as { promise: Promise<TScheduleAnalysis>; resolve: (value: TScheduleAnalysis) => void };
  handle.promise = new Promise<TScheduleAnalysis>((done) => {
    handle.resolve = done;
  });
  return handle;
};

describe("what the timeline highlights", () => {
  it("is the work items the analysis marks critical", () => {
    expect(isWorkItemCritical(analysis(), "a")).toBe(true);
    expect(isWorkItemCritical(analysis(), "c")).toBe(false);
    expect(isWorkItemCritical(analysis(), "done")).toBe(false);
  });

  it("is nothing without an analysis or for a work item it does not cover", () => {
    expect(isWorkItemCritical(undefined, "a")).toBe(false);
    expect(isWorkItemCritical(analysis(), "elsewhere")).toBe(false);
    expect(isWorkItemCritical(analysis(), undefined)).toBe(false);
    expect(getScheduleAnalysisItem(undefined, "a")).toBeUndefined();
    expect(getScheduleAnalysisItem(analysis(), "c")?.total_float).toBe(3);
  });

  it("is a dependency line only when the server lists it as critical, whichever end stores it", () => {
    expect(isDependencyCritical(analysis(), { sourceId: "a", targetId: "b", relationType: "blocking" })).toBe(true);
    expect(isDependencyCritical(analysis(), { sourceId: "a", targetId: "b", relationType: "blocked_by" })).toBe(true);
    expect(isDependencyCritical(analysis(), { sourceId: "b", targetId: "a", relationType: "blocking" })).toBe(false);
    expect(isDependencyCritical(undefined, { sourceId: "a", targetId: "b", relationType: "blocking" })).toBe(false);
  });

  it("is not a dependency line between two critical work items that leaves the later one room", () => {
    // a and b are both critical, but only their finish-to-start relation drives b
    const edge = { sourceId: "a", targetId: "b" } as const;
    expect(isDependencyCritical(analysis(), { ...edge, relationType: "finish_before" })).toBe(false);
    expect(isDependencyCritical(analysis(), { ...edge, relationType: "finish_after" })).toBe(false);
    const ss = analysis({ critical_links: [{ source: "a", target: "b", relation_type: "start_before" }] });
    expect(isDependencyCritical(ss, { ...edge, relationType: "start_after" })).toBe(true);
  });

  it("is nothing when the analysis was cut short", () => {
    const truncated = analysis({ truncated: true });
    expect(isWorkItemCritical(truncated, "a")).toBe(false);
    expect(getScheduleAnalysisItem(truncated, "c")).toBeUndefined();
    expect(isDependencyCritical(truncated, { sourceId: "a", targetId: "b", relationType: "blocking" })).toBe(false);
  });
});

describe("getScheduleAnalysisNotices", () => {
  it("says when the analysis was cut short or left a circle out", () => {
    expect(getScheduleAnalysisNotices(undefined)).toEqual([]);
    expect(getScheduleAnalysisNotices(analysis())).toEqual([]);
    expect(getScheduleAnalysisNotices(analysis({ truncated: true }))).toEqual(["truncated"]);
    expect(getScheduleAnalysisNotices(analysis({ truncated: true, cycles: [["a", "b"]] }))).toEqual([
      "truncated",
      "cycles",
    ]);
    expect(getScheduleAnalysisNotices(analysis({ inverted_count: 2 }))).toEqual(["inverted"]);
  });
});

describe("getScheduleAnalysisScope", () => {
  it("narrows the analysis to the module or cycle of the timeline", () => {
    expect(getScheduleAnalysisScope(EIssuesStoreType.MODULE, { moduleId: "m" })).toEqual({ module: "m" });
    expect(getScheduleAnalysisScope(EIssuesStoreType.CYCLE, { cycleId: "c" })).toEqual({ cycle: "c" });
  });

  it("analyses the whole project elsewhere", () => {
    expect(getScheduleAnalysisScope(EIssuesStoreType.PROJECT, { moduleId: "m", cycleId: "c" })).toEqual({});
    expect(getScheduleAnalysisScope(EIssuesStoreType.PROJECT_VIEW, {})).toEqual({});
    expect(getScheduleAnalysisScope(EIssuesStoreType.MODULE, {})).toEqual({});
  });
});

describe("getScheduleAnalysisKey", () => {
  type TWorkItem = {
    start_date?: string | null;
    finish_date?: string | null;
    target_date?: string | null;
    state_id?: string;
  };
  const workItems: Record<string, TWorkItem> = {
    a: { start_date: "2027-06-07", finish_date: "2027-06-09", state_id: "todo" },
    b: { start_date: "2027-06-10", finish_date: "2027-06-11", target_date: "2027-06-18", state_id: "todo" },
  };
  const relations: Record<string, Partial<Record<TIssueRelationTypes, string[]>>> = {
    b: { blocked_by: ["a"], relates_to: ["x"] },
    a: { blocking: ["b"] },
  };
  const key = (
    items: Record<string, TWorkItem> = workItems,
    relationMap: typeof relations = relations,
    lag: (issueId: string, relationType: TIssueRelationTypes, relatedId: string) => number = () => 0
  ) => getScheduleAnalysisKey(["a", "b"], (id) => items[id], relationMap, lag);

  it("stays the same while nothing the analysis depends on changes", () => {
    expect(key()).toBe(key());
    // a relation without dates and the order of the related ids make no difference
    expect(key(workItems, { ...relations, b: { blocked_by: ["a"], relates_to: ["x", "y"] } })).toBe(key());
    const twoBlockers = { ...relations, b: { blocked_by: ["a", "z"] } };
    const twoBlockersReversed = { ...relations, b: { blocked_by: ["z", "a"] } };
    expect(key(workItems, twoBlockers)).toBe(key(workItems, twoBlockersReversed));
  });

  it("changes with a start, finish or due date and with the state", () => {
    const changed = (change: TWorkItem) => key({ ...workItems, b: { ...workItems.b, ...change } });
    expect(changed({ start_date: "2027-06-11" })).not.toBe(key());
    expect(changed({ finish_date: "2027-06-14" })).not.toBe(key());
    expect(changed({ target_date: null })).not.toBe(key());
    expect(changed({ state_id: "done" })).not.toBe(key());
  });

  it("changes with a timeline relation and with its lag", () => {
    expect(key(workItems, { a: {}, b: {} })).not.toBe(key());
    expect(key(workItems, { ...relations, b: { start_after: ["a"] } })).not.toBe(key());
    expect(key(workItems, relations, (issueId) => (issueId === "b" ? 2 : 0))).not.toBe(key());
  });

  it("copes with work items that are not loaded", () => {
    expect(
      getScheduleAnalysisKey(
        ["gone"],
        () => undefined,
        {},
        () => 0
      )
    ).toBe("gone|||||");
  });
});

describe("IssuesTimeLineStore critical path", () => {
  const createStore = () =>
    new IssuesTimeLineStore({ issue: { issues: { getIssueById: () => undefined } } } as unknown as RootStore);

  beforeEach(() => {
    getScheduleAnalysis.mockReset();
    storage.values = {};
  });

  it("is off by default and fetches nothing while it is off", async () => {
    const store = createStore();
    expect(store.isCriticalPathEnabled).toBe(false);
    await store.fetchScheduleAnalysis("acme", "p1");
    expect(getScheduleAnalysis).not.toHaveBeenCalled();
    expect(store.scheduleAnalysis).toBeUndefined();
  });

  it("remembers the choice", () => {
    const store = createStore();
    store.toggleCriticalPath();
    expect(store.isCriticalPathEnabled).toBe(true);
    expect(createStore().isCriticalPathEnabled).toBe(true);
    store.toggleCriticalPath();
    expect(createStore().isCriticalPathEnabled).toBe(false);
  });

  it("fetches the analysis of the project, module or cycle once it is on", async () => {
    getScheduleAnalysis.mockResolvedValue(analysis());
    const store = createStore();
    store.toggleCriticalPath();
    await store.fetchScheduleAnalysis("acme", "p1", { module: "m1" });
    expect(getScheduleAnalysis).toHaveBeenCalledWith("acme", "p1", { module: "m1" });
    expect(store.scheduleAnalysis?.critical_ids).toEqual(["a", "b"]);
    expect(store.isScheduleAnalysisLoading).toBe(false);
  });

  it("keeps the analysis while the same project is fetched again and drops it for another one", async () => {
    getScheduleAnalysis.mockResolvedValue(analysis());
    const store = createStore();
    store.toggleCriticalPath();
    await store.fetchScheduleAnalysis("acme", "p1");

    const open = deferred();
    getScheduleAnalysis.mockReturnValue(open.promise);
    const again = store.fetchScheduleAnalysis("acme", "p1");
    expect(store.isScheduleAnalysisLoading).toBe(true);
    expect(store.scheduleAnalysis).toBeDefined();
    open.resolve(analysis({ critical_ids: ["c"] }));
    await again;
    expect(store.scheduleAnalysis?.critical_ids).toEqual(["c"]);

    getScheduleAnalysis.mockReturnValue(new Promise<TScheduleAnalysis>(() => undefined));
    void store.fetchScheduleAnalysis("acme", "p2");
    expect(store.scheduleAnalysis).toBeUndefined();
  });

  it("drops the answer of a request that a newer one overtook", async () => {
    const store = createStore();
    store.toggleCriticalPath();
    const firstRequest = deferred();
    getScheduleAnalysis.mockReturnValueOnce(firstRequest.promise);
    getScheduleAnalysis.mockResolvedValueOnce(analysis({ critical_ids: ["new"] }));
    const first = store.fetchScheduleAnalysis("acme", "p1");
    await store.fetchScheduleAnalysis("acme", "p1");
    firstRequest.resolve(analysis({ critical_ids: ["old"] }));
    await first;
    expect(store.scheduleAnalysis?.critical_ids).toEqual(["new"]);
    // the answer in the store is the one of the second request
    expect(store.scheduleAnalysisRequestId).toBe(2);
    expect(store.scheduleAnalysisResultId).toBe(2);
  });

  it("tells which request the analysis in the store answers", async () => {
    getScheduleAnalysis.mockResolvedValue(analysis());
    const store = createStore();
    store.toggleCriticalPath();
    await store.fetchScheduleAnalysis("acme", "p1");
    expect(store.scheduleAnalysisResultId).toBe(store.scheduleAnalysisRequestId);
    const open = deferred();
    getScheduleAnalysis.mockReturnValue(open.promise);
    const pending = store.fetchScheduleAnalysis("acme", "p1");
    // still the older answer: a component changed before this request knows it is stale
    expect(store.scheduleAnalysisResultId).toBeLessThan(store.scheduleAnalysisRequestId);
    open.resolve(analysis());
    await pending;
    expect(store.scheduleAnalysisResultId).toBe(store.scheduleAnalysisRequestId);
  });

  it("clears the analysis when the request fails, and when it is switched off", async () => {
    getScheduleAnalysis.mockResolvedValue(analysis());
    const store = createStore();
    store.toggleCriticalPath();
    await store.fetchScheduleAnalysis("acme", "p1");

    getScheduleAnalysis.mockRejectedValue(new Error("boom"));
    await expect(store.fetchScheduleAnalysis("acme", "p1")).rejects.toThrow("boom");
    expect(store.scheduleAnalysis).toBeUndefined();
    expect(store.isScheduleAnalysisLoading).toBe(false);

    getScheduleAnalysis.mockResolvedValue(analysis());
    await store.fetchScheduleAnalysis("acme", "p1");
    expect(store.scheduleAnalysis).toBeDefined();
    store.toggleCriticalPath();
    expect(store.scheduleAnalysis).toBeUndefined();
  });

  it("an answer that arrives after switching off is ignored", async () => {
    const store = createStore();
    store.toggleCriticalPath();
    const open = deferred();
    getScheduleAnalysis.mockReturnValue(open.promise);
    const pending = store.fetchScheduleAnalysis("acme", "p1");
    store.toggleCriticalPath();
    open.resolve(analysis());
    await pending;
    expect(store.scheduleAnalysis).toBeUndefined();
    expect(store.isScheduleAnalysisLoading).toBe(false);
  });

  it("refreshes with what was last asked for, and only for that project", async () => {
    getScheduleAnalysis.mockResolvedValue(analysis());
    const store = createStore();
    store.toggleCriticalPath();
    await store.refreshScheduleAnalysis("p1");
    expect(getScheduleAnalysis).not.toHaveBeenCalled();

    await store.fetchScheduleAnalysis("acme", "p1", { cycle: "c1" });
    await store.refreshScheduleAnalysis("p2");
    expect(getScheduleAnalysis).toHaveBeenCalledTimes(1);
    await store.refreshScheduleAnalysis("p1");
    expect(getScheduleAnalysis).toHaveBeenCalledTimes(2);
    expect(getScheduleAnalysis).toHaveBeenLastCalledWith("acme", "p1", { cycle: "c1" });
  });
});
