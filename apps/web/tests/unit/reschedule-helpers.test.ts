/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueActivity, TRelationRescheduleShift } from "@plane/types";
import { describe, expect, it } from "vitest";
import {
  getRescheduleDependents,
  getRescheduleMoves,
  getRescheduleOffer,
  getShiftCause,
  isRescheduleOfferEnabled,
  rescheduleFlags,
} from "@/helpers/reschedule";

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

  it("takes the workspace from the page when the entry has none", () => {
    expect(getShiftCause(entry({ workspace_detail: undefined }), "osm")?.href).toBe("/osm/browse/WDR-12/");
  });

  it("is undefined when the link cannot be built", () => {
    expect(getShiftCause(entry({ workspace_detail: undefined }))).toBeUndefined();
    expect(getShiftCause(entry({ shift_cause: { ...cause, project_identifier: "" } }))).toBeUndefined();
  });
});

const shift = (id: string): TRelationRescheduleShift => ({
  id,
  project_id: "p1",
  sequence_id: 1,
  ref: `PRJ-${id}`,
  name: id,
  start_date: "2026-01-11",
  finish_date: "2026-01-20",
  new_start_date: "2026-01-15",
  new_finish_date: "2026-01-24",
});

describe("getRescheduleOffer", () => {
  it("reads an answer from before sub-work items could follow", () => {
    const offer = getRescheduleOffer({ error_code: "relation_reschedule_available", shifts: [shift("a")] });
    expect(offer).toEqual({ shifts: [shift("a")], sub_items: [], shifts_with_sub_items: [shift("a")] });
  });

  it("reads an offer of sub-work items alone", () => {
    const offer = getRescheduleOffer({
      error_code: "relation_reschedule_available",
      shifts: [],
      sub_items: [shift("c")],
      shifts_with_sub_items: [],
    });
    expect(offer?.sub_items).toEqual([shift("c")]);
  });

  it("is null for other errors and for an offer with nothing in it", () => {
    expect(getRescheduleOffer({ error_code: "relation_date_conflict", shifts: [shift("a")] })).toBeNull();
    expect(getRescheduleOffer({ error_code: "relation_reschedule_available", shifts: [] })).toBeNull();
    expect(getRescheduleOffer(undefined)).toBeNull();
  });
});

describe("what moves with the answer", () => {
  const offer = { shifts: [shift("a")], sub_items: [shift("c")], shifts_with_sub_items: [shift("a"), shift("b")] };

  it("takes the dependents of the plan with the sub-work items when they follow", () => {
    expect(getRescheduleDependents(offer, true).map((item) => item.id)).toEqual(["a", "b"]);
    expect(getRescheduleMoves(offer, true).map((item) => item.id)).toEqual(["a", "b", "c"]);
  });

  it("takes the dependents alone when they stay", () => {
    expect(getRescheduleDependents(offer, false).map((item) => item.id)).toEqual(["a"]);
    expect(getRescheduleMoves(offer, false).map((item) => item.id)).toEqual(["a"]);
  });
});

describe("rescheduleFlags", () => {
  it("sends only what is set, and an answer about sub-work items either way", () => {
    expect(rescheduleFlags()).toEqual({});
    expect(rescheduleFlags({ offerSubItems: true })).toEqual({ offer_sub_items: true });
    expect(rescheduleFlags({ shiftDependents: true, moveSubItems: false })).toEqual({
      shift_dependents: true,
      move_sub_items: false,
    });
    expect(rescheduleFlags({ moveSubItems: true })).toEqual({ move_sub_items: true });
  });
});
