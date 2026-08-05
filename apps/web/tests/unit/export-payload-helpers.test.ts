import { describe, expect, it } from "vitest";
import { EXPORTERS_LIST, PROJECT_EXPORT_FORMATS } from "@plane/constants";
import { buildIssueExportPayload, buildProjectExportRequestBody } from "../../core/helpers/export-payload-helpers";

describe("export format constants", () => {
  it("exposes csv comma and semicolon variants for work item export", () => {
    const csvFormats = EXPORTERS_LIST.filter((format) => format.provider === "csv");

    expect(csvFormats).toHaveLength(2);
    expect(csvFormats.map((format) => format.delimiter)).toEqual([",", ";"]);
  });

  it("exposes csv formats for project configuration export", () => {
    expect(PROJECT_EXPORT_FORMATS.length).toBeGreaterThanOrEqual(2);
    expect(PROJECT_EXPORT_FORMATS.every((format) => format.provider === "csv")).toBe(true);
    expect(PROJECT_EXPORT_FORMATS[0]?.delimiter).toBe(",");
    expect(PROJECT_EXPORT_FORMATS[1]?.delimiter).toBe(";");
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

  it("builds project export request body with optional work items flag", () => {
    expect(
      buildProjectExportRequestBody(["project-1"], {
        provider: "csv",
        delimiter: ",",
      })
    ).toEqual({
      provider: "csv",
      project: ["project-1"],
      include_work_items: false,
      delimiter: ",",
    });

    expect(
      buildProjectExportRequestBody(["project-1"], {
        provider: "csv",
        delimiter: ";",
        includeWorkItems: true,
      })
    ).toEqual({
      provider: "csv",
      project: ["project-1"],
      include_work_items: true,
      delimiter: ";",
    });
  });
});
