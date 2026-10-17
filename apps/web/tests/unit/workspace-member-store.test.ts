/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { IWorkspaceMemberInvitation } from "@plane/types";
import type { IMemberRootStore } from "@/store/member";
import type { RootStore } from "@/store/root.store";
import { WorkspaceMemberStore } from "@/store/member/workspace/workspace-member.store";

const updateWorkspaceInvitation = vi.hoisted(() => vi.fn());

vi.mock("@/services/workspace.service", () => ({
  WorkspaceService: class {
    updateWorkspaceInvitation = updateWorkspaceInvitation;
  },
}));

const createStore = () =>
  new WorkspaceMemberStore({} as IMemberRootStore, { router: {}, user: {} } as unknown as RootStore);

const invitation = (id: string, role: number) => ({ id, role }) as unknown as IWorkspaceMemberInvitation;

describe("WorkspaceMemberStore.updateMemberInvitation", () => {
  beforeEach(() => {
    updateWorkspaceInvitation.mockReset();
  });

  it("updates the matching invitation optimistically and sends the request", async () => {
    updateWorkspaceInvitation.mockResolvedValue(undefined);
    const store = createStore();
    store.workspaceMemberInvitations = { acme: [invitation("a", 5), invitation("b", 15)] };

    await store.updateMemberInvitation("acme", "b", { role: 20 });

    expect(store.workspaceMemberInvitations.acme).toEqual([invitation("a", 5), invitation("b", 20)]);
    expect(updateWorkspaceInvitation).toHaveBeenCalledWith("acme", "b", { role: 20 });
  });

  it("reverts the optimistic update and rethrows when the request fails", async () => {
    const failure = new Error("boom");
    updateWorkspaceInvitation.mockRejectedValue(failure);
    const store = createStore();
    store.workspaceMemberInvitations = { acme: [invitation("a", 5), invitation("b", 15)] };

    await expect(store.updateMemberInvitation("acme", "b", { role: 20 })).rejects.toBe(failure);

    expect(store.workspaceMemberInvitations.acme).toEqual([invitation("a", 5), invitation("b", 15)]);
  });

  it("still sends the request when the invitations were never loaded", async () => {
    updateWorkspaceInvitation.mockResolvedValue(undefined);
    const store = createStore();

    await expect(store.updateMemberInvitation("acme", "b", { role: 20 })).resolves.toBeUndefined();

    expect(updateWorkspaceInvitation).toHaveBeenCalledWith("acme", "b", { role: 20 });
    expect(store.workspaceMemberInvitations.acme).toBeUndefined();
  });

  it("rethrows a failed request without creating an entry when nothing was loaded", async () => {
    const failure = new Error("boom");
    updateWorkspaceInvitation.mockRejectedValue(failure);
    const store = createStore();

    await expect(store.updateMemberInvitation("acme", "b", { role: 20 })).rejects.toBe(failure);

    expect(store.workspaceMemberInvitations.acme).toBeUndefined();
  });
});
