/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { format } from "date-fns";
import { de } from "date-fns/locale/de";
import { enUS } from "date-fns/locale/en-US";
import { pl } from "date-fns/locale/pl";
import { describe, expect, it } from "vitest";
import { getDateSelectFormatToken } from "../../components/dropdowns/date-select";

describe("getDateSelectFormatToken", () => {
  it("leaves English on the block's default style", () => {
    expect(getDateSelectFormatToken(enUS.code)).toBeUndefined();
  });

  it("uses the localized medium date for other languages, in that language's order", () => {
    const day = new Date(2026, 9, 27);
    expect(format(day, getDateSelectFormatToken(de.code) ?? "", { locale: de })).toBe("27. Okt. 2026");
    expect(format(day, getDateSelectFormatToken(pl.code) ?? "", { locale: pl })).toBe("27 paź 2026");
  });
});
