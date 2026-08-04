import { describe, expect, it } from "vitest";
import { EXPORTERS_LIST, PROJECT_EXPORT_FORMATS } from "@plane/constants";
import { buildIssueExportPayload, buildProjectExportRequestBody } from "../../core/helpers/export-payload-helpers";

describe("export format constants", () => {
  it("exposes csv comma and semicolon variants for work item export", () => {
    const csvFormats = EXPORTERS_LIST.filter((format) => format.provider === "csv");

    expect(csvFormats).toHaveLength(2);
    expect(csvFormats.map((format) => format.delimiter)).toEqual([",", ";"]);
  });

  it("exposes csv and xlsx formats for project export", () => {
    expect(PROJECT_EXPORT_FORMATS).toHaveLength(3);
    expect(PROJECT_EXPORT_FORMATS.map((format) => format.provider)).toEqual(["csv", "csv", "xlsx"]);
    expect(PROJECT_EXPORT_FORMATS[0]?.delimiter).toBe(",");
    expect(PROJECT_EXPORT_FORMATS[1]?.delimiter).toBe(";");
    expect(PROJECT_EXPORT_FORMATS[2]?.extension).toBe("xlsx");
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

  it("builds project export request body for csv and xlsx", () => {
    expect(
      buildProjectExportRequestBody(["project-1"], {
        provider: "csv",
        delimiter: ",",
      })
    ).toEqual({
      provider: "csv",
      project: ["project-1"],
      delimiter: ",",
    });

    expect(
      buildProjectExportRequestBody(["project-1"], {
        provider: "xlsx",
      })
    ).toEqual({
      provider: "xlsx",
      project: ["project-1"],
    });
  });
});
