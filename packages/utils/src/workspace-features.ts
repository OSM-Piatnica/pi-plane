/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { WORKSPACE_FEATURE_LIST } from "@plane/constants";
import type {
  TAvailableWorkspaceFeature,
  TWorkspaceFeature,
  TWorkspaceFeatureFlags,
  TWorkspaceFeatureKey,
} from "@plane/types";

/** The features that are built, and so can be switched, in list order */
export const getAvailableWorkspaceFeatures = <TKey extends string = TWorkspaceFeatureKey>(
  features: readonly TWorkspaceFeature<TKey>[] = WORKSPACE_FEATURE_LIST as readonly TWorkspaceFeature<TKey>[]
): TAvailableWorkspaceFeature<TKey>[] =>
  features.filter((feature): feature is TAvailableWorkspaceFeature<TKey> => feature.isAvailable);

/**
 * Whether there is anything to switch. While this is false the Features settings page and its
 * navigation entry do not exist for the user.
 */
export const hasAvailableWorkspaceFeatures = <TKey extends string = TWorkspaceFeatureKey>(
  features?: readonly TWorkspaceFeature<TKey>[]
): boolean => getAvailableWorkspaceFeatures(features).length > 0;

/**
 * The on/off state of every known feature for a workspace, from the `enabled_features` of the
 * workspace payload. A feature is on only when it is available and the workspace enabled it;
 * unknown keys in the payload are ignored, and everything is off while the workspace loads.
 */
export const getWorkspaceFeatureFlags = <TKey extends string = TWorkspaceFeatureKey>(
  enabledKeys: readonly string[] | null | undefined,
  features: readonly TWorkspaceFeature<TKey>[] = WORKSPACE_FEATURE_LIST as readonly TWorkspaceFeature<TKey>[]
): TWorkspaceFeatureFlags<TKey> => {
  const enabled = new Set(enabledKeys ?? []);
  const flags = {} as TWorkspaceFeatureFlags<TKey>;
  for (const feature of features) flags[feature.key] = feature.isAvailable && enabled.has(feature.key);
  return flags;
};

/** The `enabled_features` of a workspace after one switch changes, in list order, without duplicates */
export const toggleWorkspaceFeatureKey = <TKey extends string = TWorkspaceFeatureKey>(
  enabledKeys: readonly string[] | null | undefined,
  key: TKey,
  isEnabled: boolean,
  features: readonly TWorkspaceFeature<TKey>[] = WORKSPACE_FEATURE_LIST as readonly TWorkspaceFeature<TKey>[]
): TKey[] => {
  const flags = getWorkspaceFeatureFlags(enabledKeys, features);
  const feature = features.find((item) => item.key === key);
  if (feature?.isAvailable) flags[key] = isEnabled;
  return features.filter((item) => flags[item.key]).map((item) => item.key);
};
