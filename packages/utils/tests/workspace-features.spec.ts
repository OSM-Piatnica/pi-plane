/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { WORKSPACE_FEATURE_LIST, WORKSPACE_FEATURES } from "@plane/constants";
import type { TWorkspaceFeature } from "@plane/types";
import {
  getAvailableWorkspaceFeatures,
  getWorkspaceFeatureFlags,
  hasAvailableWorkspaceFeatures,
  toggleWorkspaceFeatureKey,
} from "../src/workspace-features";

type TKey = "lite" | "approvals" | "wiki";

// a list with available features exists only in this test
const available = (key: TKey): TWorkspaceFeature<TKey> => ({
  key,
  isAvailable: true,
  i18n_title: `${key}.title`,
  i18n_description: `${key}.description`,
});
const FEATURES: TWorkspaceFeature<TKey>[] = [
  available("lite"),
  { key: "approvals", isAvailable: false },
  available("wiki"),
];

describe("WORKSPACE_FEATURES as shipped", () => {
  it("knows the five switches of the roadmap", () => {
    expect(Object.keys(WORKSPACE_FEATURES)).toEqual(["lite", "approvals", "initiatives", "wiki", "raci"]);
    for (const [key, feature] of Object.entries(WORKSPACE_FEATURES)) expect(feature.key).toBe(key);
  });

  it("has Initiatives and RACI as the only available features, so only they can be on", () => {
    expect(WORKSPACE_FEATURE_LIST.filter((feature) => feature.isAvailable).map((feature) => feature.key)).toEqual([
      "initiatives",
      "raci",
    ]);
    expect(getAvailableWorkspaceFeatures().map((feature) => feature.key)).toEqual(["initiatives", "raci"]);
    expect(hasAvailableWorkspaceFeatures()).toBe(true);
    expect(getWorkspaceFeatureFlags(["lite", "approvals", "initiatives", "wiki", "raci"])).toEqual({
      lite: false,
      approvals: false,
      initiatives: true,
      wiki: false,
      raci: true,
    });
  });
});

describe("getAvailableWorkspaceFeatures", () => {
  it("keeps the available features in list order", () => {
    expect(getAvailableWorkspaceFeatures(FEATURES).map((feature) => feature.key)).toEqual(["lite", "wiki"]);
    expect(hasAvailableWorkspaceFeatures(FEATURES)).toBe(true);
  });

  it("carries the strings of the settings page", () => {
    expect(getAvailableWorkspaceFeatures(FEATURES)[0]).toMatchObject({
      i18n_title: "lite.title",
      i18n_description: "lite.description",
    });
  });

  it("is empty when nothing is available", () => {
    expect(getAvailableWorkspaceFeatures<TKey>([{ key: "approvals", isAvailable: false }])).toEqual([]);
    expect(hasAvailableWorkspaceFeatures<TKey>([])).toBe(false);
  });
});

describe("getWorkspaceFeatureFlags", () => {
  it("is all off while the workspace loads", () => {
    for (const enabled of [undefined, null, []]) {
      expect(getWorkspaceFeatureFlags(enabled, FEATURES)).toEqual({ lite: false, approvals: false, wiki: false });
    }
  });

  it("switches on what the workspace enabled", () => {
    expect(getWorkspaceFeatureFlags(["wiki"], FEATURES)).toEqual({ lite: false, approvals: false, wiki: true });
    expect(getWorkspaceFeatureFlags(["wiki", "lite"], FEATURES)).toEqual({ lite: true, approvals: false, wiki: true });
  });

  it("never switches on a feature that is not available", () => {
    expect(getWorkspaceFeatureFlags(["approvals"], FEATURES).approvals).toBe(false);
  });

  it("ignores keys it does not know", () => {
    const flags = getWorkspaceFeatureFlags(["future_feature", "__proto__", "lite"], FEATURES);
    expect(flags).toEqual({ lite: true, approvals: false, wiki: false });
    expect(Object.keys(flags)).toEqual(["lite", "approvals", "wiki"]);
  });
});

describe("toggleWorkspaceFeatureKey", () => {
  it("adds and removes a key, in list order", () => {
    expect(toggleWorkspaceFeatureKey(["wiki"], "lite", true, FEATURES)).toEqual(["lite", "wiki"]);
    expect(toggleWorkspaceFeatureKey(["lite", "wiki"], "lite", false, FEATURES)).toEqual(["wiki"]);
    expect(toggleWorkspaceFeatureKey(undefined, "wiki", true, FEATURES)).toEqual(["wiki"]);
  });

  it("does not duplicate and tolerates repeats", () => {
    expect(toggleWorkspaceFeatureKey(["wiki", "wiki"], "wiki", true, FEATURES)).toEqual(["wiki"]);
    expect(toggleWorkspaceFeatureKey([], "wiki", false, FEATURES)).toEqual([]);
  });

  it("does not switch on a feature that is not available", () => {
    expect(toggleWorkspaceFeatureKey(["lite"], "approvals", true, FEATURES)).toEqual(["lite"]);
  });
});
