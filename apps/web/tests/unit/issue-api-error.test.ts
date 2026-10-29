/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getIssueApiErrorMessage } from "../../helpers/issue-api-error";

// a translation store that holds only these entries and echoes any other key back, like the real one
const entries: Record<string, string> = {
  "issue.edit_restricted": "Only assignees may change this.",
  "issue.relation.conflict.self": "{issue} cannot be related to itself.",
  "issue.relation.conflict.date.blocked_by": "{issue} cannot start until {related} is finished.",
  "issue.relation.conflict.lag_suffix": " Relation lag: {lag} d.",
};
const t = (key: string, params?: Record<string, unknown>) =>
  (entries[key] ?? key).replace(/\{(\w+)\}/g, (_, name: string) => String(params?.[name] ?? ""));

describe("getIssueApiErrorMessage", () => {
  it("says in the user's language that the project restricts changes to assignees", () => {
    const error = { error: "English text", error_code: "work_item_edit_restricted" };
    expect(getIssueApiErrorMessage(error, "fallback", t)).toBe("Only assignees may change this.");
  });

  it("falls back to the server's sentence when the translation is missing", () => {
    const error = { error: "English text", error_code: "work_item_edit_restricted" };
    expect(getIssueApiErrorMessage(error, "fallback", (key) => key)).toBe("English text");
  });

  it("explains a relation with itself", () => {
    const error = { error_code: "relation_self", issue_ref: "PRJ-1", related_ref: "PRJ-1" };
    expect(getIssueApiErrorMessage(error, "fallback", t)).toBe("PRJ-1 cannot be related to itself.");
  });

  it("mentions the lag of a relation that refused a date", () => {
    const error = {
      error_code: "relation_date_conflict",
      relation_type: "blocked_by",
      issue_ref: "PRJ-2",
      related_ref: "PRJ-1",
      lag_days: 3,
    };
    expect(getIssueApiErrorMessage(error, "fallback", t)).toBe(
      "PRJ-2 cannot start until PRJ-1 is finished. Relation lag: 3 d."
    );
  });

  it("leaves out the lag when there is none", () => {
    const error = {
      error_code: "relation_date_conflict",
      relation_type: "blocked_by",
      issue_ref: "A",
      related_ref: "B",
      lag_days: 0,
    };
    expect(getIssueApiErrorMessage(error, "fallback", t)).toBe("A cannot start until B is finished.");
  });

  it("reads codes that a serializer wrapped in a list", () => {
    const error = { error_code: ["relation_self"], issue_ref: ["PRJ-1"], related_ref: ["PRJ-1"] };
    expect(getIssueApiErrorMessage(error, "fallback", t)).toBe("PRJ-1 cannot be related to itself.");
  });
});
