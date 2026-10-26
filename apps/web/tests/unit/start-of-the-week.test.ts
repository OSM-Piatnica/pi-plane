/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { EStartOfTheWeek } from "@plane/types";
import { resolveStartOfTheWeek } from "@/helpers/start-of-the-week";

describe("resolveStartOfTheWeek", () => {
  it("prefers the person's own choice", () => {
    expect(
      resolveStartOfTheWeek({
        profile: EStartOfTheWeek.FRIDAY,
        project: EStartOfTheWeek.MONDAY,
        workspace: EStartOfTheWeek.SATURDAY,
      })
    ).toBe(EStartOfTheWeek.FRIDAY);
  });

  it("keeps Sunday when it is the person's own choice", () => {
    expect(resolveStartOfTheWeek({ profile: EStartOfTheWeek.SUNDAY, project: EStartOfTheWeek.MONDAY })).toBe(
      EStartOfTheWeek.SUNDAY
    );
  });

  it("falls back to the project when the person follows it", () => {
    expect(
      resolveStartOfTheWeek({ profile: null, project: EStartOfTheWeek.MONDAY, workspace: EStartOfTheWeek.SATURDAY })
    ).toBe(EStartOfTheWeek.MONDAY);
  });

  it("falls back to the workspace outside a project", () => {
    expect(resolveStartOfTheWeek({ profile: null, project: undefined, workspace: EStartOfTheWeek.SATURDAY })).toBe(
      EStartOfTheWeek.SATURDAY
    );
  });

  it("ends on Sunday when nothing is set", () => {
    expect(resolveStartOfTheWeek({})).toBe(EStartOfTheWeek.SUNDAY);
    expect(resolveStartOfTheWeek({ profile: null, project: null, workspace: null })).toBe(EStartOfTheWeek.SUNDAY);
  });
});
