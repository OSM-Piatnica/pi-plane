/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { EXPORTERS_LIST } from "@plane/constants";
import { buildIssueExportPayload } from "../../core/helpers/export-payload-helpers";

describe("export format constants", () => {
  it("exposes csv comma and semicolon variants for work item export", () => {
    const csvFormats = EXPORTERS_LIST.filter((format) => format.provider === "csv");

    expect(csvFormats).toHaveLength(2);
    expect(csvFormats.map((format) => format.delimiter)).toEqual([",", ";"]);
  });
});

describe("export payload helpers", () => {
  it("includes delimiter only for csv issue export", () => {
    expect(
      buildIssueExportPayload({
        provider: { provider: "csv", delimiter: ";" },
        project: ["project-1"],
        filters: {},
      })
    ).toEqual({
      provider: "csv",
      project: ["project-1"],
      multiple: false,
      rich_filters: {},
      delimiter: ";",
    });

    expect(
      buildIssueExportPayload({
        provider: { provider: "xlsx" },
        project: ["project-1", "project-2"],
        filters: { priority: "high" },
      })
    ).toEqual({
      provider: "xlsx",
      project: ["project-1", "project-2"],
      multiple: true,
      rich_filters: { priority: "high" },
    });
  });
});
