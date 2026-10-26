/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { WorkflowStore } from "@/store/workflow.store";
import type { TDuplicateCancelOffer } from "@/store/workflow.store";
import type { RootStore } from "@/store/root.store";

const offer: TDuplicateCancelOffer = { issue: "PRJ-5 Copy of the task", originals: "PRJ-3", stateName: "Cancelled" };

describe("WorkflowStore duplicate cancel confirmation", () => {
  it("resolves with the answer given to the dialog and clears the offer", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmDuplicateCancel(offer);
    expect(store.pendingDuplicateCancel).toEqual(offer);

    store.resolveDuplicateCancel(true);

    await expect(answer).resolves.toBe(true);
    expect(store.pendingDuplicateCancel).toBeNull();
  });

  it("resolves false when the dialog is dismissed", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmDuplicateCancel(offer);
    store.resolveDuplicateCancel(false);

    await expect(answer).resolves.toBe(false);
  });

  it("declines a second offer while one is waiting", async () => {
    const store = new WorkflowStore({} as RootStore);

    const first = store.confirmDuplicateCancel(offer);
    await expect(store.confirmDuplicateCancel(offer)).resolves.toBe(false);

    store.resolveDuplicateCancel(true);
    await expect(first).resolves.toBe(true);
  });
});
