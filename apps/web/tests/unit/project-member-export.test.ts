/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { buildMemberExportParams, filenameFromContentDisposition } from "@/helpers/project-member-export";
import { parseMemberImportCsv } from "@/helpers/project-member-import";

describe("buildMemberExportParams", () => {
  it("sends the delimiter for CSV only", () => {
    expect(buildMemberExportParams({ provider: "csv", delimiter: ";" }, false)).toEqual({
      format: "csv",
      include_via_group: 0,
      delimiter: ";",
    });
    expect(buildMemberExportParams({ provider: "csv" }, true)).toEqual({
      format: "csv",
      include_via_group: 1,
      delimiter: ",",
    });
    expect(buildMemberExportParams({ provider: "xlsx" }, false)).toEqual({ format: "xlsx", include_via_group: 0 });
  });
});

describe("filenameFromContentDisposition", () => {
  it("reads the file name or falls back", () => {
    expect(filenameFromContentDisposition('attachment; filename="PEX-members-2026-10-30.csv"', "x.csv")).toBe(
      "PEX-members-2026-10-30.csv"
    );
    expect(filenameFromContentDisposition(undefined, "project-members.json")).toBe("project-members.json");
  });
});

describe("reading an exported members file", () => {
  const file =
    "Email,Group,Role,Name,Source,Via Group,Raised By Group,Joined\r\n" +
    ",Sales / Poland,5,Poland,group,,,2026-10-30\r\n" +
    "ada@example.com,,15,Ada,person,,,2026-10-30\r\n" +
    "bob@example.com,,15,Bob,person (via group),Sales,,2026-10-30\r\n" +
    "'-odd@example.com,,15,'=1+1,person,,,2026-10-30\r\n";

  it("ignores the informational columns, keeps Source and takes off the formula guard", () => {
    const parsed = parseMemberImportCsv(file);
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    expect(parsed.rows.map((row) => [row.email, row.group, row.role, row.source])).toEqual([
      ["", "Sales / Poland", "5", "group"],
      ["ada@example.com", "", "15", "person"],
      ["bob@example.com", "", "15", "person (via group)"],
      ["-odd@example.com", "", "15", "person"],
    ]);
  });
});
