/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { pathnameToAccessKey } from "../../components/settings/helper";

describe("pathnameToAccessKey", () => {
  it("returns the workspace slug and the first two path segments after it", () => {
    expect(pathnameToAccessKey("/acme/settings/members")).toEqual({
      workspaceSlug: "acme",
      accessKey: "/settings/members",
    });
  });

  it("ignores leading and trailing slashes and deeper segments", () => {
    expect(pathnameToAccessKey("/acme/settings/billing/extra/")).toEqual({
      workspaceSlug: "acme",
      accessKey: "/settings/billing",
    });
  });

  it("returns an empty access key when the path has only a workspace slug", () => {
    expect(pathnameToAccessKey("/acme")).toEqual({ workspaceSlug: "acme", accessKey: "" });
  });
});
