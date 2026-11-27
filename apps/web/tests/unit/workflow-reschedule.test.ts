/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TRelationRescheduleOffer, TRelationRescheduleShift } from "@plane/types";
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

const offer: TRelationRescheduleOffer = { shifts, sub_items: [], shifts_with_sub_items: shifts };
const withSubItems: TRelationRescheduleOffer = {
  shifts,
  sub_items: [{ ...shifts[0], id: "c1", ref: "PRJ-3", name: "Child" }],
  shifts_with_sub_items: shifts,
};

describe("WorkflowStore reschedule confirmation", () => {
  it("resolves with the answer given to the dialog and clears the request", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmReschedule(offer);
    expect(store.pendingReschedule).toEqual(offer);

    store.resolveReschedule(true);

    // no sub-work items were offered, so none move
    await expect(answer).resolves.toEqual({ confirmed: true, moveSubItems: false });
    expect(store.pendingReschedule).toBeNull();
  });

  it("resolves false when the dialog is dismissed", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmReschedule(withSubItems);
    store.resolveReschedule(false);

    await expect(answer).resolves.toEqual({ confirmed: false, moveSubItems: false });
  });

  it("ticks the sub-work items by default and passes on the person's choice", async () => {
    const store = new WorkflowStore({} as RootStore);

    const ticked = store.confirmReschedule(withSubItems);
    expect(store.rescheduleMoveSubItems).toBe(true);
    store.resolveReschedule(true);
    await expect(ticked).resolves.toEqual({ confirmed: true, moveSubItems: true });

    const unticked = store.confirmReschedule(withSubItems);
    store.setRescheduleMoveSubItems(false);
    store.resolveReschedule(true);
    await expect(unticked).resolves.toEqual({ confirmed: true, moveSubItems: false });

    // the next offer starts ticked again
    void store.confirmReschedule(withSubItems);
    expect(store.rescheduleMoveSubItems).toBe(true);
    store.resolveReschedule(false);
  });

  it("declines a second request while one is waiting, and keeps it apart from the parent reopen dialog", async () => {
    const store = new WorkflowStore({} as RootStore);

    const first = store.confirmReschedule(offer);
    await expect(store.confirmReschedule(offer)).resolves.toEqual({ confirmed: false, moveSubItems: false });
    const parents = store.confirmParentReopen([{ id: "p", name: "Parent", sequence_id: 1 }]);

    store.resolveReschedule(true);
    await expect(first).resolves.toEqual({ confirmed: true, moveSubItems: false });
    expect(store.pendingParentReopen).not.toBeNull();
    store.resolveParentReopen(false);
    await expect(parents).resolves.toBe(false);
  });
});
