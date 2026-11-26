/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TWorkspaceFeature, TWorkspaceFeatureKey } from "@plane/types";

/**
 * The workspace feature switches. A record over the key union, so a key added to the union does
 * not compile until it is listed here.
 *
 * To make a feature available, set `isAvailable: true`, give it a title and a description
 * (`pi-extensions.json`, every locale), and set the same key to `True` in
 * `apps/api/plane/utils/workspace_features.py`. A unit test compares the two lists.
 * See `docs/workspace-features.md`.
 */
export const WORKSPACE_FEATURES: { [TKey in TWorkspaceFeatureKey]: TWorkspaceFeature & { key: TKey } } = {
  lite: { key: "lite", isAvailable: false },
  approvals: { key: "approvals", isAvailable: false },
  initiatives: { key: "initiatives", isAvailable: false },
  wiki: { key: "wiki", isAvailable: false },
  raci: {
    key: "raci",
    isAvailable: true,
    i18n_title: "workspace_features.items.raci.title",
    i18n_description: "workspace_features.items.raci.description",
  },
};

/** The feature switches, in the order of the Features settings page */
export const WORKSPACE_FEATURE_LIST: readonly TWorkspaceFeature[] = Object.values(WORKSPACE_FEATURES);
