/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  SPREADSHEET_WORK_ITEM_COLUMN_KEY as WORK_ITEM,
  buildSpreadsheetColumnWidths,
  clampSpreadsheetColumnWidth,
  sanitizeSpreadsheetColumnWidths,
} from "../../helpers/spreadsheet-column-width";

describe("clampSpreadsheetColumnWidth", () => {
  it("keeps property columns between 96 and 640 and rounds to whole pixels", () => {
    expect(clampSpreadsheetColumnWidth("state", 10)).toBe(96);
    expect(clampSpreadsheetColumnWidth("state", 9999)).toBe(640);
    expect(clampSpreadsheetColumnWidth("state", 200.4)).toBe(200);
  });

  it("keeps the work item column between 240 and 512", () => {
    expect(clampSpreadsheetColumnWidth(WORK_ITEM, 100)).toBe(240);
    expect(clampSpreadsheetColumnWidth(WORK_ITEM, 900)).toBe(512);
    expect(clampSpreadsheetColumnWidth(WORK_ITEM, 300)).toBe(300);
  });
});

describe("sanitizeSpreadsheetColumnWidths", () => {
  it("drops anything that is not a positive number and clamps the rest", () => {
    expect(
      sanitizeSpreadsheetColumnWidths({
        state: 200,
        priority: "wide",
        labels: -5,
        cycle: 0,
        link: Infinity,
        due_date: 10,
      })
    ).toEqual({ state: 200, due_date: 96 });
  });

  it("ignores a saved value that is not an object", () => {
    for (const raw of [null, undefined, "x", 5, ["a"]]) expect(sanitizeSpreadsheetColumnWidths(raw)).toEqual({});
  });
});

describe("buildSpreadsheetColumnWidths", () => {
  const measured = { [WORK_ITEM]: 700, state: 144, priority: 144, assignee: 180 };

  it("freezes the property columns at their measured width and sets the dragged one", () => {
    expect(buildSpreadsheetColumnWidths("priority", 220, measured, {})).toEqual({
      state: 144,
      priority: 220,
      assignee: 180,
    });
  });

  it("leaves the work item column to take the remaining space until it is resized itself", () => {
    expect(buildSpreadsheetColumnWidths("state", 200, measured, {})[WORK_ITEM]).toBeUndefined();
    expect(buildSpreadsheetColumnWidths(WORK_ITEM, 320, measured, {})[WORK_ITEM]).toBe(320);
  });

  it("keeps a work item width that was saved earlier", () => {
    expect(buildSpreadsheetColumnWidths("state", 200, measured, { [WORK_ITEM]: 400 })[WORK_ITEM]).toBe(400);
  });

  it("clamps the dragged column", () => {
    expect(buildSpreadsheetColumnWidths("state", 1, measured, {}).state).toBe(96);
  });
});
