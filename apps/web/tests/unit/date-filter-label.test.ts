/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getDateFilterLabel } from "../../helpers/date-filter-label";

// A stand-in for `t` that fills `{date}` into the English template for the key.
const templates: Record<string, string> = {
  "date_phrases.after_date": "After {date}",
  "date_phrases.before_date": "Before {date}",
};
const t = (key: string, params?: Record<string, unknown>) =>
  (templates[key] ?? key).replace("{date}", String(params?.date ?? ""));
const formatDate = (date: string) => `<${date}>`;

describe("getDateFilterLabel", () => {
  it("words an 'after' filter through the translated template", () => {
    expect(getDateFilterLabel("2024-01-01", "after", formatDate, t)).toBe("After <2024-01-01>");
  });

  it("words a 'before' filter through the translated template", () => {
    expect(getDateFilterLabel("2024-01-01", "before", formatDate, t)).toBe("Before <2024-01-01>");
  });

  it("keeps an unknown direction readable instead of dropping it", () => {
    expect(getDateFilterLabel("2024-01-01", "during", formatDate, t)).toBe("During <2024-01-01>");
  });

  it("leaves the date empty when it cannot be formatted", () => {
    expect(getDateFilterLabel("nope", "after", () => undefined, t)).toBe("After ");
  });
});
