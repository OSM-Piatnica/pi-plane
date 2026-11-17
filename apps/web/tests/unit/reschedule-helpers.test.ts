/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueActivity } from "@plane/types";
import { describe, expect, it } from "vitest";
import { getShiftCause, isRescheduleOfferEnabled } from "@/helpers/reschedule";

type TEntry = Pick<TIssueActivity, "field" | "shift_cause" | "workspace_detail">;

const cause = { id: "i12", project_id: "p1", sequence_id: 12, project_identifier: "WDR" };
const entry = (overrides: Partial<TEntry> = {}): TEntry => ({
  field: "start_date",
  shift_cause: cause,
  workspace_detail: { slug: "osm" } as TIssueActivity["workspace_detail"],
  ...overrides,
});

describe("isRescheduleOfferEnabled", () => {
  it("is on unless the project switched it off", () => {
    expect(isRescheduleOfferEnabled(undefined)).toBe(true);
    expect(isRescheduleOfferEnabled(null)).toBe(true);
    expect(isRescheduleOfferEnabled({})).toBe(true);
    expect(isRescheduleOfferEnabled({ is_reschedule_offer_enabled: true })).toBe(true);
    expect(isRescheduleOfferEnabled({ is_reschedule_offer_enabled: false })).toBe(false);
  });
});

describe("getShiftCause", () => {
  it("names and links the work item whose change moved this one", () => {
    expect(getShiftCause(entry())).toEqual({ ref: "WDR-12", href: "/osm/browse/WDR-12/" });
    expect(getShiftCause(entry({ field: "finish_date" }))?.ref).toBe("WDR-12");
  });

  it("is undefined for a date changed by hand", () => {
    expect(getShiftCause(entry({ shift_cause: null }))).toBeUndefined();
    expect(getShiftCause(entry({ shift_cause: undefined }))).toBeUndefined();
    expect(getShiftCause(undefined)).toBeUndefined();
  });

  it("is undefined for entries of other fields, which use the identifier for something else", () => {
    expect(getShiftCause(entry({ field: "blocked_by" }))).toBeUndefined();
  });

  it("is undefined when the link cannot be built", () => {
    expect(getShiftCause(entry({ workspace_detail: undefined }))).toBeUndefined();
    expect(getShiftCause(entry({ shift_cause: { ...cause, project_identifier: "" } }))).toBeUndefined();
  });
});
