/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { DEFAULT_PROFILE_RICH_FILTERS, resolveProfileRichFilters } from "@/helpers/profile-default-filters";

describe("resolveProfileRichFilters", () => {
  it("shows the work to do and in progress when nothing was ever chosen", () => {
    expect(resolveProfileRichFilters(undefined)).toEqual({ state_group__in: "unstarted,started" });
    expect(resolveProfileRichFilters(null)).toBe(DEFAULT_PROFILE_RICH_FILTERS);
  });

  it("keeps the filters the person has chosen", () => {
    const chosen = { priority__in: "urgent" };
    expect(resolveProfileRichFilters(chosen)).toBe(chosen);
  });

  it("keeps an empty set the person cleared on purpose", () => {
    expect(resolveProfileRichFilters({})).toEqual({});
  });
});
