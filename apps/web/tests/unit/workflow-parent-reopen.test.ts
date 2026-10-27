/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { WorkflowStore } from "@/store/workflow.store";
import type { RootStore } from "@/store/root.store";

const parents = [{ id: "p1", name: "Parent", sequence_id: 1 }];

describe("WorkflowStore parent reopen confirmation", () => {
  it("resolves with the answer given to the dialog and clears the request", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmParentReopen(parents);
    expect(store.pendingParentReopen).toEqual(parents);

    store.resolveParentReopen(true);

    await expect(answer).resolves.toBe(true);
    expect(store.pendingParentReopen).toBeNull();
  });

  it("resolves false when the dialog is dismissed", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmParentReopen(parents);
    store.resolveParentReopen(false);

    await expect(answer).resolves.toBe(false);
  });

  it("declines a second request while one is waiting", async () => {
    const store = new WorkflowStore({} as RootStore);

    const first = store.confirmParentReopen(parents);
    await expect(store.confirmParentReopen(parents)).resolves.toBe(false);

    store.resolveParentReopen(true);
    await expect(first).resolves.toBe(true);
  });
});
