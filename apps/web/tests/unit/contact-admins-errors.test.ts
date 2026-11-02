/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getAdminMessageFailure } from "../../helpers/contact-admins-errors";

describe("getAdminMessageFailure", () => {
  it("tells a message sent too often from any other failure", () => {
    expect(getAdminMessageFailure({ status: 429, data: { code: "RATE_LIMITED" } })).toBe("rate_limited");
    expect(getAdminMessageFailure({ status: 429 })).toBe("rate_limited");
    expect(getAdminMessageFailure({ data: { code: "RATE_LIMITED" } })).toBe("rate_limited");
  });

  it("calls everything else a plain failure", () => {
    expect(getAdminMessageFailure({ status: 400, data: { error: "Write a message first" } })).toBe("other");
    expect(getAdminMessageFailure(undefined)).toBe("other");
    expect(getAdminMessageFailure(new Error("network"))).toBe("other");
  });
});
