/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { IUserLite } from "@plane/types";
import { isProjectLead } from "../../helpers/project-lead";

const user = (id: string) => ({ id }) as IUserLite;

describe("isProjectLead", () => {
  it("matches the lead sent as a user object or as an id", () => {
    expect(isProjectLead(user("u1"), "u1")).toBe(true);
    expect(isProjectLead("u1", "u1")).toBe(true);
  });

  it("is false for another user, no lead or no signed-in user", () => {
    expect(isProjectLead(user("u1"), "u2")).toBe(false);
    expect(isProjectLead(null, "u1")).toBe(false);
    expect(isProjectLead(undefined, "u1")).toBe(false);
    expect(isProjectLead(user("u1"), undefined)).toBe(false);
    expect(isProjectLead("", "")).toBe(false);
  });
});
