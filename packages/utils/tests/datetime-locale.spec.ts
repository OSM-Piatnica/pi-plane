/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { de, ja, pl } from "date-fns/locale";
import { describe, expect, it } from "vitest";
import {
  calculateTimeAgo,
  renderFormattedDate,
  renderFormattedDateWithoutYear,
  renderFormattedTime,
} from "../src/datetime";

describe("date helpers with a locale", () => {
  it("keep their English output when no locale is given", () => {
    expect(renderFormattedDate("2024-01-05")).toBe("Jan 05, 2024");
    expect(renderFormattedDateWithoutYear("2024-01-05")).toBe("Jan 05");
    expect(renderFormattedTime("2024-01-05T13:00:00", "12-hour")).toBe("01:00 PM");
  });

  it("name the month in the given locale", () => {
    expect(renderFormattedDate("2024-01-05", "MMM dd, yyyy", pl)).toBe("sty 05, 2024");
    expect(renderFormattedDate("2024-03-05", "d. MMMM yyyy", de)).toBe("5. März 2024");
    expect(renderFormattedDateWithoutYear("2024-01-05", pl)).toBe("sty 05");
  });

  it("use the locale's own date order with a localized token", () => {
    expect(renderFormattedDate("2024-01-05", "PP", pl)).toBe("5 sty 2024");
  });

  it("localize the AM/PM marker of the 12-hour clock", () => {
    expect(renderFormattedTime("2024-01-05T13:00:00", "12-hour", ja)).toBe("01:00 午後");
  });

  it("word the time-ago text in the given locale", () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
    expect(calculateTimeAgo(threeDaysAgo)).toBe("3 days ago");
    expect(calculateTimeAgo(threeDaysAgo, de)).toBe("vor 3 Tagen");
  });
});
