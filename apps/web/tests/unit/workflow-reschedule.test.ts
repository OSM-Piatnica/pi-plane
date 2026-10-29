/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TRelationRescheduleShift } from "@plane/types";
import { WorkflowStore } from "@/store/workflow.store";
import type { RootStore } from "@/store/root.store";

const shifts: TRelationRescheduleShift[] = [
  {
    id: "i1",
    project_id: "p1",
    sequence_id: 2,
    ref: "PRJ-2",
    name: "Dependent",
    start_date: "2026-01-11",
    finish_date: "2026-01-20",
    new_start_date: "2026-01-15",
    new_finish_date: "2026-01-24",
  },
];

describe("WorkflowStore reschedule confirmation", () => {
  it("resolves with the answer given to the dialog and clears the request", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmReschedule(shifts);
    expect(store.pendingReschedule).toEqual(shifts);

    store.resolveReschedule(true);

    await expect(answer).resolves.toBe(true);
    expect(store.pendingReschedule).toBeNull();
  });

  it("resolves false when the dialog is dismissed", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmReschedule(shifts);
    store.resolveReschedule(false);

    await expect(answer).resolves.toBe(false);
  });

  it("declines a second request while one is waiting, and keeps it apart from the parent reopen dialog", async () => {
    const store = new WorkflowStore({} as RootStore);

    const first = store.confirmReschedule(shifts);
    await expect(store.confirmReschedule(shifts)).resolves.toBe(false);
    const parents = store.confirmParentReopen([{ id: "p", name: "Parent", sequence_id: 1 }]);

    store.resolveReschedule(true);
    await expect(first).resolves.toBe(true);
    expect(store.pendingParentReopen).not.toBeNull();
    store.resolveParentReopen(false);
    await expect(parents).resolves.toBe(false);
  });
});
