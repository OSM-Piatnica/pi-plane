/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// store
import { BaseWorkspaceRootStore } from "@/store/workspace";
import type { RootStore } from "@/plane-web/store/root.store";

export class WorkspaceRootStore extends BaseWorkspaceRootStore {
  // oxlint-disable-next-line no-useless-constructor -- deliberate extension-point constructor kept for subclass/override parity
  constructor(_rootStore: RootStore) {
    super(_rootStore);
  }

  // actions
  /**
   * Mutate workspace members activity
   * @param workspaceSlug
   */
  mutateWorkspaceMembersActivity = async (_workspaceSlug: string) => {
    // No-op in default/CE version
  };
}
