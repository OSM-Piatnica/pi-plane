/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { EUserWorkspaceRoles } from "@plane/types";
import { getWorkspaceFeaturesPageAccess } from "@/components/settings/workspace/features-access";

describe("getWorkspaceFeaturesPageAccess", () => {
  it("waits while the membership loads", () => {
    expect(getWorkspaceFeaturesPageAccess(undefined)).toBe("loading");
  });

  it("lets workspace admins in", () => {
    expect(getWorkspaceFeaturesPageAccess(EUserWorkspaceRoles.ADMIN)).toBe("allowed");
  });

  it("turns members and guests away", () => {
    expect(getWorkspaceFeaturesPageAccess(EUserWorkspaceRoles.MEMBER)).toBe("denied");
    expect(getWorkspaceFeaturesPageAccess(EUserWorkspaceRoles.GUEST)).toBe("denied");
  });
});
