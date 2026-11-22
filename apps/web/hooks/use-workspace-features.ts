/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAvailableWorkspaceFeature, TWorkspaceFeatureFlags, TWorkspaceFeatureKey } from "@plane/types";
import { getAvailableWorkspaceFeatures, getWorkspaceFeatureFlags } from "@plane/utils";
import { useWorkspace } from "@/hooks/store/use-workspace";

type TUseWorkspaceFeatures = {
  /** On/off for every known feature in the current workspace; all off while it loads */
  features: TWorkspaceFeatureFlags;
  isFeatureEnabled: (key: TWorkspaceFeatureKey) => boolean;
  /** The features that are built, and so have a switch on the Features settings page */
  availableFeatures: TAvailableWorkspaceFeature[];
  updateFeature: (workspaceSlug: string, key: TWorkspaceFeatureKey, isEnabled: boolean) => Promise<void>;
};

/**
 * The feature switches of the current workspace (see `docs/workspace-features.md`).
 * Call it from an `observer` component: the state comes from the workspace store.
 */
export const useWorkspaceFeatures = (): TUseWorkspaceFeatures => {
  const { currentWorkspace, feature } = useWorkspace();
  const features = getWorkspaceFeatureFlags(currentWorkspace?.enabled_features);

  return {
    features,
    isFeatureEnabled: (key) => features[key],
    availableFeatures: getAvailableWorkspaceFeatures(),
    updateFeature: feature.updateFeature,
  };
};
