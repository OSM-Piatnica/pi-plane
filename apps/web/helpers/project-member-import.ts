/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TProjectMemberImportRow, TProjectMemberImportSummary } from "@plane/types";

/** Rows sent to the API in one request, which accepts at most 5000. */
export const MEMBER_IMPORT_CHUNK_SIZE = 1000;

export const MEMBER_IMPORT_SAMPLE_CSV =
  "Email,Group,Role\n" +
  "jane.doe@example.com,,15\n" +
  "john.smith@example.com,,20\n" +
  ",Sales,15\n" +
  ',"Sales / Poland",5\n';

export type TParsedMemberCsv =
  | { ok: true; rows: TProjectMemberImportRow[] }
  | { ok: false; error: "empty" | "missing_columns" | "no_rows" };

/** Splits CSV text into cells: quoted cells may hold the separator, quotes ("") and line breaks. */
export const parseCsvText = (text: string): string[][] => {
  const source = text.replace(/^﻿/, "");
  const firstLine = source.split(/\r?\n/, 1)[0] ?? "";
  // spreadsheets in many locales write semicolons
  const separator = !firstLine.includes(",") && firstLine.includes(";") ? ";" : ",";
  const records: string[][] = [];
  let record: string[] = [];
  let cell = "";
  let quoted = false;
  const endCell = () => {
    record.push(cell);
    cell = "";
  };
  const endRecord = () => {
    endCell();
    if (record.some((value) => value.trim() !== "")) records.push(record);
    record = [];
  };
  for (let index = 0; index < source.length; index++) {
    const char = source[index];
    if (quoted) {
      if (char === '"' && source[index + 1] === '"') {
        cell += '"';
        index++;
      } else if (char === '"') quoted = false;
      else cell += char;
    } else if (char === '"') quoted = true;
    else if (char === separator) endCell();
    else if (char === "\n") endRecord();
    else if (char !== "\r") cell += char;
  }
  if (cell !== "" || record.length > 0) endRecord();
  return records;
};

const normalizeHeader = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[\s_-]+/g, "");

/** Reads the members CSV: columns Email and/or Group, and Role, in any order, any case. */
export const parseMemberImportCsv = (text: string): TParsedMemberCsv => {
  const records = parseCsvText(text);
  if (records.length === 0) return { ok: false, error: "empty" };
  const headers = records[0].map(normalizeHeader);
  const email = headers.indexOf("email");
  const group = headers.indexOf("group");
  const role = headers.indexOf("role");
  if (role === -1 || (email === -1 && group === -1)) return { ok: false, error: "missing_columns" };
  const rows = records.slice(1).map((record, index): TProjectMemberImportRow => {
    const row: TProjectMemberImportRow = { row: index + 2, role: (record[role] ?? "").trim() };
    if (email !== -1) row.email = (record[email] ?? "").trim();
    if (group !== -1) row.group = (record[group] ?? "").trim();
    return row;
  });
  return rows.length === 0 ? { ok: false, error: "no_rows" } : { ok: true, rows };
};

export const chunkRows = <T>(rows: T[], size: number = MEMBER_IMPORT_CHUNK_SIZE): T[][] => {
  const chunks: T[][] = [];
  for (let start = 0; start < rows.length; start += size) chunks.push(rows.slice(start, start + size));
  return chunks;
};

export const emptyMemberImportSummary = (): TProjectMemberImportSummary => ({
  people: { added: 0, reactivated: 0, already_members: 0, skipped: 0 },
  groups: { added: 0, updated: 0, skipped: 0 },
  skipped: [],
});

/** The answers to the chunks of one file, added up. */
export const mergeMemberImportSummaries = (summaries: TProjectMemberImportSummary[]): TProjectMemberImportSummary =>
  summaries.reduce((total, summary) => {
    for (const key of Object.keys(total.people) as (keyof TProjectMemberImportSummary["people"])[])
      total.people[key] += summary.people[key];
    for (const key of Object.keys(total.groups) as (keyof TProjectMemberImportSummary["groups"])[])
      total.groups[key] += summary.groups[key];
    total.skipped.push(...summary.skipped);
    return total;
  }, emptyMemberImportSummary());

const csvCell = (value: string | number) => `"${String(value).replaceAll('"', '""')}"`;

/** The skipped rows as a CSV the admin can fix and import again. */
export const skippedRowsToCsv = (skipped: TProjectMemberImportSummary["skipped"]): string =>
  [
    "Row,Type,Value,Reason",
    ...skipped.map((item) => [item.row, item.type, item.value, item.reason].map(csvCell).join(",")),
  ].join("\n") + "\n";

/**
 * Sends the rows in chunks, one chunk after the other, so rows of a later chunk see what an earlier one changed;
 * returns the answer of every chunk.
 */
export const importMemberRowsInChunks = async (
  rows: TProjectMemberImportRow[],
  send: (chunk: TProjectMemberImportRow[]) => Promise<TProjectMemberImportSummary>
): Promise<TProjectMemberImportSummary[]> => {
  const chunks = chunkRows<TProjectMemberImportRow>(rows);
  // written as a chain, not a loop: each chunk starts only after the previous one is answered
  const sendFrom = async (
    index: number,
    answers: TProjectMemberImportSummary[]
  ): Promise<TProjectMemberImportSummary[]> => {
    if (index >= chunks.length) return answers;
    return sendFrom(index + 1, [...answers, await send(chunks[index])]);
  };
  return sendFrom(0, []);
};
