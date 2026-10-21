/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { canGoBackInHistory, getWorkspaceHomeHref } from "@/helpers/home-navigation.helper";

describe("getWorkspaceHomeHref", () => {
  it("points at the workspace home with a trailing slash", () => {
    expect(getWorkspaceHomeHref("acme")).toBe("/acme/");
  });

  it("falls back to the root route without a workspace", () => {
    expect(getWorkspaceHomeHref(undefined)).toBe("/");
    expect(getWorkspaceHomeHref("")).toBe("/");
  });
});

describe("canGoBackInHistory", () => {
  it("is false for a page opened directly", () => {
    expect(canGoBackInHistory(1)).toBe(false);
  });

  it("is true once there is an earlier entry", () => {
    expect(canGoBackInHistory(2)).toBe(true);
  });
});
