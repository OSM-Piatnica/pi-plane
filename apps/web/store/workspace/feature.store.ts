/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, runInAction } from "mobx";
import { WORKSPACE_FEATURE_LIST } from "@plane/constants";
import type { IWorkspace, TWorkspaceFeature, TWorkspaceFeatureKey } from "@plane/types";
import { toggleWorkspaceFeatureKey } from "@plane/utils";
import { WorkspaceService } from "@/services/workspace.service";

/** The part of the workspace store the feature switches need */
type TWorkspaceSource = {
  workspaces: Record<string, IWorkspace>;
  getWorkspaceBySlug: (workspaceSlug: string) => IWorkspace | null;
};

type TWorkspaceFeatureService = Pick<WorkspaceService, "updateWorkspaceFeatures">;

export interface IWorkspaceFeatureStore {
  /**
   * Switches a feature on or off for the workspace. The enabled features live on the workspace
   * itself (`IWorkspace.enabled_features`), so everything that reads them follows at once; a
   * failed request puts the previous state back and rethrows.
   */
  updateFeature: (workspaceSlug: string, key: TWorkspaceFeatureKey, isEnabled: boolean) => Promise<void>;
}

export class WorkspaceFeatureStore implements IWorkspaceFeatureStore {
  private workspaceStore: TWorkspaceSource;
  private workspaceService: TWorkspaceFeatureService;
  private features: readonly TWorkspaceFeature[];

  constructor(
    workspaceStore: TWorkspaceSource,
    workspaceService: TWorkspaceFeatureService = new WorkspaceService(),
    // the known switches; only tests pass another list
    features: readonly TWorkspaceFeature[] = WORKSPACE_FEATURE_LIST
  ) {
    makeObservable(this, {
      updateFeature: action,
    });
    this.workspaceStore = workspaceStore;
    this.workspaceService = workspaceService;
    this.features = features;
  }

  private setEnabledFeatures = (workspaceId: string, enabledFeatures: string[] | undefined) => {
    runInAction(() => {
      const workspace = this.workspaceStore.workspaces[workspaceId];
      if (workspace) this.workspaceStore.workspaces[workspaceId] = { ...workspace, enabled_features: enabledFeatures };
    });
  };

  updateFeature = async (workspaceSlug: string, key: TWorkspaceFeatureKey, isEnabled: boolean) => {
    const workspace = this.workspaceStore.getWorkspaceBySlug(workspaceSlug);
    if (!workspace) throw new Error("Workspace not found");
    const before = workspace.enabled_features;

    this.setEnabledFeatures(workspace.id, toggleWorkspaceFeatureKey(before, key, isEnabled, this.features));
    try {
      const states = await this.workspaceService.updateWorkspaceFeatures(workspaceSlug, { [key]: isEnabled });
      // the answer is the truth: it lists every available feature of the workspace
      this.setEnabledFeatures(
        workspace.id,
        Object.keys(states ?? {}).filter((featureKey) => states[featureKey])
      );
    } catch (error) {
      this.setEnabledFeatures(workspace.id, before);
      throw error;
    }
  };
}
