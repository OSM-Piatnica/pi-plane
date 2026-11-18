/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { WorkflowStore } from "@/store/workflow.store";
import type { RootStore } from "@/store/root.store";

const choice = { mode: "add" as const, names: ["Epic"] };

describe("WorkflowStore sub-work item choice", () => {
  it("resolves with the answer given to the dialog and clears the request", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmSubIssues(choice);
    expect(store.pendingSubIssuesChoice).toEqual(choice);

    store.resolveSubIssues(true);

    await expect(answer).resolves.toBe(true);
    expect(store.pendingSubIssuesChoice).toBeNull();
  });

  it("resolves false when the dialog is dismissed", async () => {
    const store = new WorkflowStore({} as RootStore);

    const answer = store.confirmSubIssues(choice);
    store.resolveSubIssues(false);

    await expect(answer).resolves.toBe(false);
  });

  it("declines a second request while one is waiting", async () => {
    const store = new WorkflowStore({} as RootStore);

    const first = store.confirmSubIssues(choice);
    await expect(store.confirmSubIssues({ mode: "remove", names: ["Other"] })).resolves.toBe(false);
    store.resolveSubIssues(true);
    await expect(first).resolves.toBe(true);
  });
});
