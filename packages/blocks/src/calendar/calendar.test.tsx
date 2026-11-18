/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { pl } from "date-fns/locale";
import type { Locale } from "date-fns";
import type { CalendarLabels } from "@makeplane/propel/components/calendar";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { setLanguage } from "@plane/i18n";
import { Calendar } from "./calendar";

// These run against the real translations.

const JUNE_15 = new Date(2025, 5, 15);

function renderCalendar(extra: { locale?: Locale; labels?: CalendarLabels } = {}) {
  return render(
    <Calendar
      mode="single"
      defaultMonth={JUNE_15}
      today={JUNE_15}
      selected={new Date(2025, 5, 16)}
      onSelect={() => {}}
      {...extra}
    />
  );
}

const useLanguage = async (language: "en" | "pl" | "de") => {
  await act(async () => {
    await setLanguage(language);
  });
};

beforeEach(async () => {
  await useLanguage("en");
});

afterEach(async () => {
  cleanup();
  await useLanguage("en");
});

describe("Calendar", () => {
  it("names the month and year buttons and the arrows in English", () => {
    renderCalendar();

    expect(screen.getByRole("button", { name: "Choose the month, June" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Choose the year, 2025" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Previous month" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Next month" })).toBeDefined();
  });

  it("names them in the interface language, with the month in the calendar's locale", async () => {
    await useLanguage("pl");
    renderCalendar({ locale: pl });

    expect(screen.getByRole("button", { name: "Wybierz miesiąc, czerwca" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Wybierz rok, 2025" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Poprzedni miesiąc" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Następny miesiąc" })).toBeDefined();
  });

  it("names today and the selected day in English", () => {
    renderCalendar();

    expect(screen.getByRole("button", { name: "Today, Sunday, June 15th, 2025" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Monday, June 16th, 2025, selected" })).toBeDefined();
  });

  it("names today and the selected day in the interface language", async () => {
    await useLanguage("pl");
    renderCalendar({ locale: pl });

    expect(screen.getByRole("button", { name: "Dzisiaj, niedziela, 15 czerwca 2025" })).toBeDefined();
    expect(screen.getByRole("button", { name: "poniedziałek, 16 czerwca 2025, wybrano" })).toBeDefined();
  });

  it("names the month and year views", async () => {
    const user = userEvent.setup();
    await useLanguage("pl");
    renderCalendar({ locale: pl });

    await user.click(screen.getByRole("button", { name: "Wybierz miesiąc, czerwca" }));
    expect(screen.getByRole("group", { name: "Wybierz miesiąc w roku 2025" })).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Wybierz rok, 2025" }));
    expect(screen.getByRole("group", { name: "Wybierz rok od 2020 do 2031" })).toBeDefined();
  });

  it("names the arrows of the month and year views", async () => {
    const user = userEvent.setup();
    await useLanguage("pl");
    renderCalendar({ locale: pl });

    await user.click(screen.getByRole("button", { name: "Wybierz miesiąc, czerwca" }));
    expect(screen.getByRole("button", { name: "Poprzedni rok" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Następny rok" })).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Wybierz rok, 2025" }));
    expect(screen.getByRole("button", { name: "Poprzednie 12 lat" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Następne 12 lat" })).toBeDefined();
  });

  it("follows a language change while the calendar is open", async () => {
    renderCalendar();
    expect(screen.getByRole("button", { name: "Previous month" })).toBeDefined();

    await useLanguage("de");

    expect(screen.getByRole("button", { name: "Vorheriger Monat" })).toBeDefined();
  });

  it("lets the caller's own labels win", () => {
    renderCalendar({ labels: { labelNext: () => "Forward" } });

    expect(screen.getByRole("button", { name: "Forward" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Previous month" })).toBeDefined();
  });
});
