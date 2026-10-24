/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { normalizeDefaultWorkspacePath, withDefaultWorkspaceParams } from "@/app/compat/next/route-policy-context";

describe("normalizeDefaultWorkspacePath", () => {
  it("shortens the work item browse route of the default workspace", () => {
    expect(normalizeDefaultWorkspacePath("/acme/browse/AB-12", "acme")).toBe("/i/AB-12");
    expect(normalizeDefaultWorkspacePath("/acme/browse/AB-12/", "acme")).toBe("/i/AB-12");
  });

  it("keeps the query string and hash", () => {
    expect(normalizeDefaultWorkspacePath("/acme/browse/AB-12?peekId=1#comments", "acme")).toBe(
      "/i/AB-12?peekId=1#comments"
    );
  });

  it("leaves every other route of the default workspace alone", () => {
    for (const path of [
      "/acme/projects/1/issues",
      "/acme/settings/projects/1",
      "/acme/browse/AB-12/extra",
      "/acme/archives/browse/AB-12",
    ]) {
      expect(normalizeDefaultWorkspacePath(path, "acme")).toBe(path);
    }
  });

  it("leaves other workspaces alone", () => {
    expect(normalizeDefaultWorkspacePath("/other/browse/AB-12", "acme")).toBe("/other/browse/AB-12");
    expect(normalizeDefaultWorkspacePath("/acme-two/browse/AB-12", "acme")).toBe("/acme-two/browse/AB-12");
  });

  it("does nothing without a default workspace or for non-absolute paths", () => {
    expect(normalizeDefaultWorkspacePath("/acme/browse/AB-12")).toBe("/acme/browse/AB-12");
    expect(normalizeDefaultWorkspacePath("acme/browse/AB-12", "acme")).toBe("acme/browse/AB-12");
    expect(normalizeDefaultWorkspacePath("https://example.com/acme/browse/AB-12", "acme")).toBe(
      "https://example.com/acme/browse/AB-12"
    );
  });

  it("treats a slug as text, not as a pattern", () => {
    expect(normalizeDefaultWorkspacePath("/axme/browse/AB-12", "a.me")).toBe("/axme/browse/AB-12");
    expect(normalizeDefaultWorkspacePath("/a.me/browse/AB-12", "a.me")).toBe("/i/AB-12");
  });
});

describe("withDefaultWorkspaceParams", () => {
  it("supplies the default workspace on the compact route", () => {
    expect(withDefaultWorkspaceParams({ workItem: "AB-12" }, "acme")).toEqual({
      workItem: "AB-12",
      workspaceSlug: "acme",
    });
  });

  it("never overrides a workspace named in the URL", () => {
    const params = { workspaceSlug: "other", workItem: "AB-12" };
    expect(withDefaultWorkspaceParams(params, "acme")).toBe(params);
  });

  it("only applies to work item routes", () => {
    const params = { projectId: "1" };
    expect(withDefaultWorkspaceParams(params, "acme")).toBe(params);
  });

  it("does nothing until the default workspace is known", () => {
    const params = { workItem: "AB-12" };
    expect(withDefaultWorkspaceParams(params)).toBe(params);
  });
});
