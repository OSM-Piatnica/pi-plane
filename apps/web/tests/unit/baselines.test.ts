/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TBaselineVariance, TBaselineVarianceItem, TProjectBaseline } from "@plane/types";
import {
  formatSignedDays,
  getBarVariance,
  getBaselineBarPosition,
  getBaselineDeadlineX,
  getBaselineKey,
  getBaselineTooltipLines,
  getComparedBaseline,
  getVarianceText,
  hasBaselineMoved,
} from "@/helpers/baseline.helper";
import { BaselineStore } from "@/store/timeline/baseline.store";

const service = vi.hoisted(() => ({
  list: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  remove: vi.fn(),
  getVariance: vi.fn(),
}));
const storage = vi.hoisted(() => ({ values: {} as Record<string, unknown> }));

vi.mock("@/services/project/project-baseline.service", () => ({
  ProjectBaselineService: class {
    list = service.list;
    create = service.create;
    update = service.update;
    remove = service.remove;
    getVariance = service.getVariance;
  },
}));

vi.mock("@/hooks/use-local-storage", () => ({
  getValueFromLocalStorage: (key: string, defaultValue: unknown) => storage.values[key] ?? defaultValue,
  setValueIntoLocalStorage: (key: string, value: unknown) => {
    storage.values[key] = value;
    return true;
  },
}));

// a translation that shows the key and its values, so the tests see what was asked for
const t = ((key: string, values?: Record<string, unknown>) =>
  values ? `${key}(${JSON.stringify(values)})` : key) as unknown as Parameters<typeof getVarianceText>[1];

const item = (overrides: Partial<TBaselineVarianceItem> = {}): TBaselineVarianceItem => ({
  in_baseline: true,
  baseline_start_date: "2027-06-01",
  start_date: "2027-06-01",
  start_date_variance: 0,
  baseline_finish_date: "2027-06-04",
  finish_date: "2027-06-04",
  finish_date_variance: 0,
  baseline_target_date: null,
  target_date: null,
  ...overrides,
});

const baseline = (overrides: Partial<TProjectBaseline> = {}): TProjectBaseline => ({
  id: "b1",
  name: "Plan",
  description: "",
  is_active: true,
  item_count: 2,
  created_at: "2027-06-01T08:00:00Z",
  created_by: "u1",
  project: "p1",
  ...overrides,
});

const variance = (overrides: Partial<TBaselineVariance> = {}): TBaselineVariance => ({
  baseline: baseline(),
  items: { a: item() },
  summary: { baseline_end: "2027-06-04", current_end: "2027-06-04", end_variance: 0 },
  weekend_days: [0, 6],
  ...overrides,
});

/** A request whose answer the test gives when it wants to. */
const deferred = () => {
  const handle = {} as { promise: Promise<TBaselineVariance>; resolve: (value: TBaselineVariance) => void };
  handle.promise = new Promise<TBaselineVariance>((done) => {
    handle.resolve = done;
  });
  return handle;
};

// a chart that starts on 1 June 2027 and draws each day 20 px wide
const DAY = 20;
const getPosition = (date: string) => (Number(date.slice(8, 10)) - 1) * DAY;

describe("baseline helpers", () => {
  it("draws the trace from the saved start to the end of the saved finish day", () => {
    expect(getBaselineBarPosition(item(), getPosition, DAY)).toEqual({ left: 0, width: 4 * DAY });
    // a work item that had only one of the dates gets a trace one day wide
    expect(getBaselineBarPosition(item({ baseline_start_date: null }), getPosition, DAY)).toEqual({
      left: 3 * DAY,
      width: DAY,
    });
    expect(getBaselineBarPosition(item({ baseline_finish_date: null }), getPosition, DAY)).toEqual({
      left: 0,
      width: DAY,
    });
    expect(
      getBaselineBarPosition(item({ baseline_start_date: null, baseline_finish_date: null }), getPosition, DAY)
    ).toBeUndefined();
    expect(getBaselineBarPosition(item(), getPosition, undefined)).toBeUndefined();
    expect(getBaselineBarPosition(item(), () => undefined, DAY)).toBeUndefined();
  });

  it("uses the schedule, not the due date, for the trace", () => {
    const withDeadline = item({ baseline_target_date: "2027-06-30", target_date: "2027-06-10" });
    expect(getBaselineBarPosition(withDeadline, getPosition, DAY)).toEqual({ left: 0, width: 4 * DAY });
    // only a moved start or finish is a moved bar
    expect(hasBaselineMoved(withDeadline)).toBe(false);
    expect(hasBaselineMoved(item({ finish_date: "2027-06-07" }))).toBe(true);
    expect(hasBaselineMoved(item({ start_date: null }))).toBe(true);
    expect(hasBaselineMoved(item({ in_baseline: false, baseline_start_date: null, baseline_finish_date: null }))).toBe(
      false
    );
    expect(hasBaselineMoved(undefined)).toBe(false);
  });

  it("puts a marker in the middle of the saved due date only when the deadline moved", () => {
    expect(
      getBaselineDeadlineX(item({ baseline_target_date: "2027-06-11", target_date: "2027-06-18" }), getPosition, DAY)
    ).toBe(10 * DAY + DAY / 2);
    // also when the due date was cleared since
    expect(getBaselineDeadlineX(item({ baseline_target_date: "2027-06-11" }), getPosition, DAY)).toBe(
      10 * DAY + DAY / 2
    );
    expect(
      getBaselineDeadlineX(item({ baseline_target_date: "2027-06-11", target_date: "2027-06-11" }), getPosition, DAY)
    ).toBeUndefined();
    expect(getBaselineDeadlineX(item({ target_date: "2027-06-11" }), getPosition, DAY)).toBeUndefined();
  });

  it("shows the variance of the finish, else of the start, and none for a work item the baseline does not know", () => {
    expect(getBarVariance(item({ finish_date_variance: 3, start_date_variance: 1 }))).toBe(3);
    expect(getBarVariance(item({ finish_date_variance: null, start_date_variance: -2 }))).toBe(-2);
    expect(getBarVariance(item({ in_baseline: false, finish_date_variance: null, start_date_variance: null }))).toBe(
      null
    );
    expect(getBarVariance(undefined)).toBe(null);
  });

  it("formats a variance with its sign", () => {
    expect(formatSignedDays(3)).toBe("+3");
    expect(formatSignedDays(-2)).toBe("−2");
    expect(formatSignedDays(0)).toBe("0");
    expect(getVarianceText(0, t)).toBe("baseline.on_plan");
    expect(getVarianceText(3, t)).toBe('baseline.variance_days({"days":"+3"})');
    expect(getVarianceText(-1, t)).toBe('baseline.variance_days({"days":"−1"})');
  });

  it("says in the tooltip what the baseline had and how far the start and the finish moved", () => {
    const lines = getBaselineTooltipLines(
      item({ start_date_variance: 0, finish_date_variance: 3, target_date: "2027-06-30" }),
      "Plan",
      { start: "Start", finish: "Finish" },
      (date) => date.slice(5),
      t
    );
    expect(lines).toEqual([
      'baseline.bar_tooltip({"name":"Plan","start":"06-01","end":"06-04"})',
      'Start: baseline.on_plan · Finish: baseline.variance_days({"days":"+3"})',
    ]);
    const cleared = getBaselineTooltipLines(
      item({ start_date_variance: null, finish_date_variance: null }),
      "Plan",
      { start: "Start", finish: "Finish" },
      (date) => date.slice(5),
      t
    );
    expect(cleared).toHaveLength(1);
  });

  it("changes the key when a date of a loaded work item changes", () => {
    const dates: Record<string, { start_date?: string; finish_date?: string; target_date?: string }> = {
      a: { start_date: "2027-06-01", finish_date: "2027-06-04" },
    };
    const before = getBaselineKey(["a"], (id) => dates[id]);
    dates.a = { ...dates.a, target_date: "2027-06-11" };
    expect(getBaselineKey(["a"], (id) => dates[id])).not.toBe(before);
  });

  it("compares with the picked baseline, else the active one", () => {
    const baselines = [baseline({ id: "new" }), baseline({ id: "old", is_active: false })];
    expect(getComparedBaseline(baselines, undefined)?.id).toBe("new");
    expect(getComparedBaseline(baselines, "old")?.id).toBe("old");
    expect(getComparedBaseline(baselines, "gone")?.id).toBe("new");
    expect(getComparedBaseline(undefined, undefined)).toBeUndefined();
  });
});

describe("BaselineStore", () => {
  beforeEach(() => {
    Object.values(service).forEach((mock) => mock.mockReset());
    storage.values = {};
  });

  it("is hidden by default, fetches nothing while hidden and remembers the choice", async () => {
    const store = new BaselineStore();
    expect(store.isBaselineShown).toBe(false);
    await store.fetchVariance("acme", "p1");
    expect(service.getVariance).not.toHaveBeenCalled();
    store.toggleBaseline();
    expect(new BaselineStore().isBaselineShown).toBe(true);
  });

  it("fetches the comparison of the project, module or cycle, with the picked baseline", async () => {
    service.getVariance.mockResolvedValue(variance());
    const store = new BaselineStore();
    store.toggleBaseline();
    await store.fetchVariance("acme", "p1", { module: "m1" });
    expect(service.getVariance).toHaveBeenLastCalledWith("acme", "p1", { module: "m1" });
    expect(store.variance?.items.a).toBeDefined();
    expect(store.isVarianceLoading).toBe(false);

    const revision = store.revision;
    store.selectBaseline("old");
    expect(store.revision).toBe(revision + 1);
    await store.fetchVariance("acme", "p1", { module: "m1" });
    expect(service.getVariance).toHaveBeenLastCalledWith("acme", "p1", { module: "m1", baseline: "old" });
  });

  it("drops the answer of an overtaken request, and everything when hidden", async () => {
    const store = new BaselineStore();
    store.toggleBaseline();
    const firstAnswer = deferred();
    service.getVariance.mockReturnValueOnce(firstAnswer.promise);
    service.getVariance.mockResolvedValueOnce(variance({ items: { new: item() } }));
    const first = store.fetchVariance("acme", "p1");
    await store.fetchVariance("acme", "p1");
    firstAnswer.resolve(variance({ items: { old: item() } }));
    await first;
    expect(Object.keys(store.variance?.items ?? {})).toEqual(["new"]);

    store.toggleBaseline();
    expect(store.variance).toBeUndefined();
  });

  it("clears the comparison when the request fails", async () => {
    service.getVariance.mockResolvedValueOnce(variance());
    const store = new BaselineStore();
    store.toggleBaseline();
    await store.fetchVariance("acme", "p1");
    service.getVariance.mockRejectedValueOnce({ error: "boom" });
    await expect(store.fetchVariance("acme", "p1")).rejects.toEqual({ error: "boom" });
    expect(store.variance).toBeUndefined();
    expect(store.isVarianceLoading).toBe(false);
  });

  it("saving makes the new baseline the active one and shows it", async () => {
    service.list.mockResolvedValue({ baselines: [baseline({ id: "old" })], max_baselines: 20 });
    service.create.mockResolvedValue(baseline({ id: "new", name: "Plan 2" }));
    const store = new BaselineStore();
    await store.fetchBaselines("acme", "p1");
    store.selectBaseline("old");
    const revision = store.revision;
    await store.saveBaseline("acme", "p1", "Plan 2");
    expect(service.create).toHaveBeenCalledWith("acme", "p1", { name: "Plan 2" });
    expect(store.baselines?.map((row) => [row.id, row.is_active])).toEqual([
      ["new", true],
      ["old", false],
    ]);
    expect(store.selectedBaselineId).toBeUndefined();
    expect(store.isBaselineShown).toBe(true);
    expect(store.revision).toBeGreaterThan(revision);
  });

  it("activating, renaming and deleting keep the list in step", async () => {
    service.list.mockResolvedValue({
      baselines: [baseline({ id: "new" }), baseline({ id: "old", is_active: false })],
      max_baselines: 20,
    });
    const store = new BaselineStore();
    await store.fetchBaselines("acme", "p1");

    service.update.mockResolvedValueOnce(baseline({ id: "old", is_active: true }));
    await store.updateBaseline("acme", "p1", "old", { is_active: true });
    expect(store.baselines?.map((row) => [row.id, row.is_active])).toEqual([
      ["new", false],
      ["old", true],
    ]);

    const revision = store.revision;
    service.update.mockResolvedValueOnce(baseline({ id: "new", name: "Renamed", is_active: false }));
    await store.updateBaseline("acme", "p1", "new", { name: "Renamed" });
    expect(store.baselines?.[0].name).toBe("Renamed");
    // a new name does not change the comparison
    expect(store.revision).toBe(revision);

    store.selectBaseline("new");
    service.remove.mockResolvedValueOnce(undefined);
    await store.deleteBaseline("acme", "p1", "new");
    expect(store.baselines?.map((row) => row.id)).toEqual(["old"]);
    expect(store.selectedBaselineId).toBeUndefined();
  });

  it("forgets the baselines and the pick of another project", async () => {
    service.list.mockResolvedValueOnce({ baselines: [baseline({ id: "x" })], max_baselines: 20 });
    const store = new BaselineStore();
    await store.fetchBaselines("acme", "p1");
    store.selectBaseline("x");
    service.list.mockReturnValueOnce(new Promise(() => undefined));
    void store.fetchBaselines("acme", "p2");
    expect(store.baselines).toBeUndefined();
    expect(store.selectedBaselineId).toBeUndefined();
  });
});
