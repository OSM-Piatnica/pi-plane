import { describe, expect, it } from "vitest";
import {
  getProjectImportLink,
  isValidProjectImportFile,
  isValidProjectImportSize,
  MAX_PROJECT_CSV_SIZE_BYTES,
} from "../../core/helpers/project-csv-helpers";

describe("project-csv-helpers", () => {
  it("accepts csv files by extension", () => {
    expect(isValidProjectImportFile(new File(["a"], "project.csv", { type: "text/csv" }))).toBe(true);
    expect(isValidProjectImportFile(new File(["a"], "project.zip", { type: "application/zip" }))).toBe(false);
    expect(isValidProjectImportFile(new File(["a"], "project.txt", { type: "text/plain" }))).toBe(false);
  });

  it("validates file size for csv", () => {
    const smallCsv = new File(["a"], "project.csv", { type: "text/csv" });
    expect(isValidProjectImportSize(smallCsv)).toBe(true);
    expect(isValidProjectImportSize(smallCsv, 0)).toBe(false);
    expect(MAX_PROJECT_CSV_SIZE_BYTES).toBe(15 * 1024 * 1024);
  });

  it("builds project link after import", () => {
    expect(getProjectImportLink("acme", "project-1")).toBe("/acme/projects/project-1/issues");
  });
});
