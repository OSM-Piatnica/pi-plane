/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TIssueType } from "@plane/types";
import { getMilestoneDateChange, isMilestoneType, planWorkItemDateChange } from "@plane/utils";
import {
  getNewCatalogueKeys,
  toggleCatalogueKey,
} from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/work-item-types/work-item-type-catalogue-helpers";
import {
  buildIssueTypePayloadFromForm,
  mapIssueTypeToFormValues,
} from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/work-item-types/work-item-type-payload-helpers";
import { DEFAULT_WORK_ITEM_TYPE_FORM } from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/work-item-types/work-item-type-form.types";
import { isMilestoneLate } from "../../helpers/milestone";
import { getDescriptionForTypeChange } from "../../helpers/work-item-type-template";

const BUG_TEMPLATE = "<h3>Expected result</h3><p></p><h3>Actual result</h3><p></p>";
const STORY_TEMPLATE = "<p>As a …, I want …, so that ….</p>";

describe("catalogue selection", () => {
  it("selects the entries the workspace does not have", () => {
    expect(
      getNewCatalogueKeys([
        { key: "task", existing_type_id: "t1" },
        { key: "bug", existing_type_id: null },
        { key: "milestone", existing_type_id: null },
      ])
    ).toEqual(["bug", "milestone"]);
  });

  it("toggles a key", () => {
    expect(toggleCatalogueKey(["bug"], "story")).toEqual(["bug", "story"]);
    expect(toggleCatalogueKey(["bug", "story"], "bug")).toEqual(["story"]);
  });
});

describe("description template in the type form", () => {
  it("sends an empty editor as no template", () => {
    expect(
      buildIssueTypePayloadFromForm({ ...DEFAULT_WORK_ITEM_TYPE_FORM, name: "Bug", descriptionTemplate: "<p></p>" })
    ).toMatchObject({ description_template: null });
  });

  it("sends and reads back a template", () => {
    const payload = buildIssueTypePayloadFromForm({
      ...DEFAULT_WORK_ITEM_TYPE_FORM,
      name: "Bug",
      descriptionTemplate: BUG_TEMPLATE,
    });
    expect(payload.description_template).toBe(BUG_TEMPLATE);
    const row = { name: "Bug", description_template: BUG_TEMPLATE, logo_props: {}, is_active: true } as TIssueType;
    expect(mapIssueTypeToFormValues(row).descriptionTemplate).toBe(BUG_TEMPLATE);
    expect(mapIssueTypeToFormValues({ ...row, description_template: null }).descriptionTemplate).toBe("");
  });
});

describe("getDescriptionForTypeChange", () => {
  it("fills an empty description", () => {
    expect(getDescriptionForTypeChange({ currentHtml: "<p></p>", template: BUG_TEMPLATE, lastApplied: null })).toBe(
      BUG_TEMPLATE
    );
    expect(getDescriptionForTypeChange({ currentHtml: undefined, template: BUG_TEMPLATE, lastApplied: null })).toBe(
      BUG_TEMPLATE
    );
  });

  it("never replaces what a person wrote", () => {
    expect(
      getDescriptionForTypeChange({ currentHtml: "<p>Crash on save</p>", template: BUG_TEMPLATE, lastApplied: null })
    ).toBeUndefined();
    expect(
      getDescriptionForTypeChange({
        currentHtml: "<h3>Expected result</h3><p>Saved</p><h3>Actual result</h3><p></p>",
        template: STORY_TEMPLATE,
        lastApplied: BUG_TEMPLATE,
      })
    ).toBeUndefined();
  });

  it("swaps an untouched template for the template of the new type", () => {
    // the editor writes the HTML back in its own form; the text decides
    const asEdited = "<h3>Expected result</h3><p></p>\n<h3>Actual result</h3><p></p>";
    expect(
      getDescriptionForTypeChange({ currentHtml: asEdited, template: STORY_TEMPLATE, lastApplied: BUG_TEMPLATE })
    ).toBe(STORY_TEMPLATE);
  });

  it("takes an untouched template away for a type without one", () => {
    expect(getDescriptionForTypeChange({ currentHtml: BUG_TEMPLATE, template: null, lastApplied: BUG_TEMPLATE })).toBe(
      "<p></p>"
    );
    expect(getDescriptionForTypeChange({ currentHtml: "<p></p>", template: null, lastApplied: null })).toBeUndefined();
  });
});

describe("milestones", () => {
  it("knows the kind", () => {
    expect(isMilestoneType({ kind: "milestone" })).toBe(true);
    expect(isMilestoneType({ kind: "standard" })).toBe(false);
    expect(isMilestoneType(undefined)).toBe(false);
  });

  it("is late only when the finish is after the due date", () => {
    expect(isMilestoneLate("2026-03-06", "2026-03-04")).toBe(true);
    expect(isMilestoneLate("2026-03-04", "2026-03-04")).toBe(false);
    expect(isMilestoneLate("2026-03-02", "2026-03-04")).toBe(false);
    expect(isMilestoneLate("2026-03-06", null)).toBe(false);
  });

  it("moves start and finish together, as the server does", () => {
    expect(getMilestoneDateChange({ finish_date: "2026-03-06" })).toEqual({
      start_date: "2026-03-06",
      finish_date: "2026-03-06",
    });
    expect(getMilestoneDateChange({ start_date: "2026-03-02" })).toEqual({
      start_date: "2026-03-02",
      finish_date: "2026-03-02",
    });
    expect(getMilestoneDateChange({ start_date: "2026-03-02", finish_date: "2026-03-06" })).toEqual({
      start_date: "2026-03-06",
      finish_date: "2026-03-06",
    });
    expect(getMilestoneDateChange({ duration: 5 })).toEqual({});
    expect(getMilestoneDateChange({ target_date: "2026-03-04" })).toEqual({ target_date: "2026-03-04" });
  });

  it("previews a one-day milestone and leaves other work items alone", () => {
    const current = { start_date: "2026-03-02", finish_date: "2026-03-02", duration: 1, dates_initialized: true };
    const milestone = planWorkItemDateChange(current, { finish_date: "2026-03-06" }, true, [], true);
    expect(milestone.patch).toMatchObject({ start_date: "2026-03-06", finish_date: "2026-03-06", duration: 1 });
    const task = planWorkItemDateChange(current, { finish_date: "2026-03-06" }, true, []);
    expect(task.patch).toMatchObject({ finish_date: "2026-03-06", duration: 5 });
    expect(task.patch.start_date).toBeUndefined();
  });
});
