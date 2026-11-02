/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  MEMBER_IMPORT_SAMPLE_CSV,
  chunkRows,
  importMemberRowsInChunks,
  emptyMemberImportSummary,
  mergeMemberImportSummaries,
  parseCsvText,
  parseMemberImportCsv,
  skippedRowsToCsv,
} from "@/helpers/project-member-import";

describe("parseCsvText", () => {
  it("handles quotes, escaped quotes, line breaks in cells, CRLF and a byte order mark", () => {
    const text = '﻿a,b\r\n"x, y","say ""hi"""\r\n"two\nlines",z\r\n\r\n';
    expect(parseCsvText(text)).toEqual([
      ["a", "b"],
      ["x, y", 'say "hi"'],
      ["two\nlines", "z"],
    ]);
  });
  it("reads semicolon separated files", () => {
    expect(parseCsvText("Email;Role\na@b.c;15")).toEqual([
      ["Email", "Role"],
      ["a@b.c", "15"],
    ]);
  });
});

describe("parseMemberImportCsv", () => {
  it("reads the sample file, with people and group rows", () => {
    const parsed = parseMemberImportCsv(MEMBER_IMPORT_SAMPLE_CSV);
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    expect(parsed.rows).toEqual([
      { row: 2, email: "jane.doe@example.com", group: "", role: "15" },
      { row: 3, email: "john.smith@example.com", group: "", role: "20" },
      { row: 4, email: "", group: "Sales", role: "15" },
      { row: 5, email: "", group: "Sales / Poland", role: "5" },
    ]);
  });
  it("matches headers in any case and order, and works with only an Email or only a Group column", () => {
    const people = parseMemberImportCsv("ROLE, mail\n15,a@b.c");
    expect(people).toEqual({ ok: false, error: "missing_columns" });
    const groups = parseMemberImportCsv(" role ,GROUP\n5,Sales");
    expect(groups).toEqual({ ok: true, rows: [{ row: 2, group: "Sales", role: "5" }] });
    const emails = parseMemberImportCsv("Role,Email\n5,a@b.c");
    expect(emails).toEqual({ ok: true, rows: [{ row: 2, email: "a@b.c", role: "5" }] });
  });
  it("reports an empty file, a file without the columns and a file without rows", () => {
    expect(parseMemberImportCsv("")).toEqual({ ok: false, error: "empty" });
    expect(parseMemberImportCsv("Name,Age\nx,1")).toEqual({ ok: false, error: "missing_columns" });
    expect(parseMemberImportCsv("Email,Role\n")).toEqual({ ok: false, error: "no_rows" });
  });
});

describe("chunking and merging", () => {
  it("splits rows into chunks", () => {
    expect(chunkRows([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
    expect(chunkRows([], 2)).toEqual([]);
  });
  it("adds up the summaries of the chunks", () => {
    const first = emptyMemberImportSummary();
    first.people.added = 2;
    first.groups.added = 1;
    first.skipped.push({ row: 2, type: "group", value: "X", code: "unknown_group", reason: "r" });
    const second = emptyMemberImportSummary();
    second.people.added = 1;
    second.people.skipped = 1;
    second.groups.updated = 3;
    const total = mergeMemberImportSummaries([first, second]);
    expect(total.people).toEqual({ added: 3, reactivated: 0, already_members: 0, skipped: 1 });
    expect(total.groups).toEqual({ added: 1, updated: 3, skipped: 0 });
    expect(total.skipped).toHaveLength(1);
    // the inputs are not changed
    expect(first.people.added).toBe(2);
  });
});

describe("skippedRowsToCsv", () => {
  it("quotes the cells", () => {
    const csv = skippedRowsToCsv([
      { row: 4, type: "group", value: 'A "b"', code: "unknown_group", reason: "No, none" },
    ]);
    expect(csv).toBe('Row,Type,Value,Reason\n"4","group","A ""b""","No, none"\n');
  });
});

describe("importMemberRowsInChunks", () => {
  it("sends one chunk after the other and returns every answer in order", async () => {
    const events: string[] = [];
    const rows = Array.from({ length: 2500 }, (_, i) => ({ row: i + 1, email: `p${i}@x.test`, role: "15" }));
    const answers = await importMemberRowsInChunks(rows, async (chunk) => {
      events.push(`start ${chunk[0].row}`);
      await Promise.resolve();
      events.push(`end ${chunk[0].row}`);
      return { people: { added: chunk.length } } as never;
    });
    expect(events).toEqual(["start 1", "end 1", "start 1001", "end 1001", "start 2001", "end 2001"]);
    expect(answers.map((answer) => (answer as never as { people: { added: number } }).people.added)).toEqual([
      1000, 1000, 500,
    ]);
  });
});
