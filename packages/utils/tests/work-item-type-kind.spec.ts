/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  getIssueTypeKind,
  isEpicKind,
  isSystemManagedKind,
  isSystemManagedType,
  SYSTEM_MANAGED_ISSUE_TYPE_KINDS,
} from "../src/work-item/type-kind";

describe("getIssueTypeKind", () => {
  it("reads the kind the server sent", () => {
    expect(getIssueTypeKind({ kind: "milestone", is_epic: false })).toBe("milestone");
    expect(getIssueTypeKind({ kind: "review", is_epic: false })).toBe("review");
  });

  it("falls back to is_epic when cached data has no kind", () => {
    expect(getIssueTypeKind({ is_epic: true })).toBe("epic");
    expect(getIssueTypeKind({ is_epic: false })).toBe("standard");
  });

  it("lets the kind decide when the two disagree", () => {
    expect(getIssueTypeKind({ kind: "standard", is_epic: true })).toBe("standard");
  });

  it("treats a missing type as the standard kind", () => {
    expect(getIssueTypeKind(undefined)).toBe("standard");
    expect(getIssueTypeKind(null)).toBe("standard");
    expect(getIssueTypeKind({})).toBe("standard");
  });
});

describe("isSystemManagedKind", () => {
  it("is true for approval and review only", () => {
    expect(isSystemManagedKind("approval")).toBe(true);
    expect(isSystemManagedKind("review")).toBe(true);
    expect(isSystemManagedKind("standard")).toBe(false);
    expect(isSystemManagedKind("epic")).toBe(false);
    expect(isSystemManagedKind("milestone")).toBe(false);
  });

  it("is false without a kind", () => {
    expect(isSystemManagedKind(undefined)).toBe(false);
    expect(isSystemManagedKind(null)).toBe(false);
  });

  it("matches the list the API uses", () => {
    expect([...SYSTEM_MANAGED_ISSUE_TYPE_KINDS].toSorted()).toEqual(["approval", "review"]);
  });
});

describe("isSystemManagedType", () => {
  it("reads the kind of the type", () => {
    expect(isSystemManagedType({ kind: "approval", is_epic: false })).toBe(true);
    expect(isSystemManagedType({ kind: "epic", is_epic: true })).toBe(false);
  });

  it("is false for cached types without a kind and for no type", () => {
    expect(isSystemManagedType({ is_epic: true })).toBe(false);
    expect(isSystemManagedType(undefined)).toBe(false);
  });
});

describe("isEpicKind", () => {
  it("is true for the epic kind", () => {
    expect(isEpicKind({ kind: "epic", is_epic: true })).toBe(true);
  });

  it("falls back to is_epic without a kind", () => {
    expect(isEpicKind({ is_epic: true })).toBe(true);
    expect(isEpicKind({ is_epic: false })).toBe(false);
  });

  it("is false for the other kinds and for no type", () => {
    expect(isEpicKind({ kind: "milestone", is_epic: false })).toBe(false);
    expect(isEpicKind({ kind: "approval", is_epic: false })).toBe(false);
    expect(isEpicKind(null)).toBe(false);
  });
});
