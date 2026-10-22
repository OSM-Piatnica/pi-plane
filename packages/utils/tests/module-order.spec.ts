/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { IModule, TModuleOrderByOptions } from "@plane/types";
import { orderModules } from "../src/module";

const mod = (
  id: string,
  extra: { name?: string; total?: number; done?: number; target_date?: string | null; created_at?: string } = {}
): IModule =>
  ({
    id,
    name: extra.name ?? id,
    total_issues: extra.total ?? 0,
    completed_issues: extra.done ?? 0,
    cancelled_issues: 0,
    target_date: extra.target_date ?? null,
    created_at: extra.created_at ?? "2026-01-01T00:00:00Z",
    sort_order: 0,
  }) as unknown as IModule;

const ids = (modules: IModule[]) => modules.map((m) => m.id);
const order = (modules: IModule[], key: TModuleOrderByOptions) => ids(orderModules(modules, key));

describe("orderModules", () => {
  it("sorts names naturally in both directions", () => {
    const modules = [mod("a", { name: "Module 10" }), mod("b", { name: "Module 2" }), mod("c", { name: "Module 1" })];
    expect(order(modules, "name")).toEqual(["c", "b", "a"]);
    expect(order(modules, "-name")).toEqual(["a", "b", "c"]);
  });

  it("sorts by the number of work items in both directions", () => {
    const modules = [
      mod("some", { total: 5 }),
      mod("many", { total: 20 }),
      mod("empty", { total: 0 }),
      mod("few", { total: 2 }),
    ];
    expect(order(modules, "issues_length")).toEqual(["empty", "few", "some", "many"]);
    expect(order(modules, "-issues_length")).toEqual(["many", "some", "few", "empty"]);
  });

  it("sorts by created date in both directions", () => {
    const modules = [
      mod("middle", { created_at: "2026-02-01T00:00:00Z" }),
      mod("newest", { created_at: "2026-03-01T00:00:00Z" }),
      mod("oldest", { created_at: "2026-01-01T00:00:00Z" }),
    ];
    expect(order(modules, "created_at")).toEqual(["oldest", "middle", "newest"]);
    expect(order(modules, "-created_at")).toEqual(["newest", "middle", "oldest"]);
  });

  it("sorts by target date in both directions and keeps modules without one last", () => {
    const modules = [
      mod("none"),
      mod("late", { target_date: "2026-12-01" }),
      mod("early", { target_date: "2026-03-01" }),
      mod("mid", { target_date: "2026-06-01" }),
    ];
    expect(order(modules, "target_date")).toEqual(["early", "mid", "late", "none"]);
    expect(order(modules, "-target_date")).toEqual(["late", "mid", "early", "none"]);
  });

  it("sorts by progress in both directions and treats a module without work items as 0%", () => {
    const modules = [mod("half", { total: 4, done: 2 }), mod("done", { total: 2, done: 2 }), mod("empty")];
    expect(order(modules, "progress")).toEqual(["empty", "half", "done"]);
    expect(order(modules, "-progress")).toEqual(["done", "half", "empty"]);
  });

  it("does not change the input and returns [] for no modules or no key", () => {
    const modules = [mod("b", { name: "B" }), mod("a", { name: "A" })];
    orderModules(modules, "name");
    expect(ids(modules)).toEqual(["b", "a"]);
    expect(orderModules([], "name")).toEqual([]);
    expect(orderModules(modules, undefined)).toEqual([]);
  });
});
