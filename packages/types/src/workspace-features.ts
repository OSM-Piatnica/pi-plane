/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Keys of the parts of the product a workspace admin can switch on or off for a workspace.
 * The API keeps the same list in `apps/api/plane/utils/workspace_features.py`.
 * See `docs/workspace-features.md`.
 */
export type TWorkspaceFeatureKey = "lite" | "approvals" | "initiatives" | "wiki" | "raci";

/**
 * One feature switch. A feature that is not built yet is known but not available: it cannot be
 * switched on and is not listed anywhere. The strings of the settings page are required from the
 * moment a feature becomes available, not before.
 */
export type TWorkspaceFeature<TKey extends string = TWorkspaceFeatureKey> =
  | { key: TKey; isAvailable: false }
  | {
      key: TKey;
      isAvailable: true;
      /** i18n key of the feature's name on the Features settings page */
      i18n_title: string;
      /** i18n key of the one-line description under the name */
      i18n_description: string;
    };

export type TAvailableWorkspaceFeature<TKey extends string = TWorkspaceFeatureKey> = Extract<
  TWorkspaceFeature<TKey>,
  { isAvailable: true }
>;

/** Whether each feature is on for a workspace. Every key is present; unknown means off. */
export type TWorkspaceFeatureFlags<TKey extends string = TWorkspaceFeatureKey> = Record<TKey, boolean>;
