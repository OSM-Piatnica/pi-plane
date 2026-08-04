import { describe, expect, it } from "vitest";
import {
  getProjectImportLink,
  isValidProjectCsvFile,
  isValidProjectCsvSize,
  MAX_PROJECT_CSV_SIZE_BYTES,
} from "../../core/helpers/project-csv-helpers";

describe("project-csv-helpers", () => {
  it("accepts csv files by extension", () => {
    expect(isValidProjectCsvFile(new File(["a"], "project.csv", { type: "text/csv" }))).toBe(true);
    expect(isValidProjectCsvFile(new File(["a"], "project.txt", { type: "text/plain" }))).toBe(false);
  });

  it("validates file size", () => {
    const small = new File(["a"], "project.csv", { type: "text/csv" });
    expect(isValidProjectCsvSize(small)).toBe(true);
    expect(isValidProjectCsvSize(small, 0)).toBe(false);
    expect(MAX_PROJECT_CSV_SIZE_BYTES).toBeGreaterThan(0);
  });

  it("builds project link after import", () => {
    expect(getProjectImportLink("acme", "project-1")).toBe("/acme/projects/project-1/issues");
  });
});
