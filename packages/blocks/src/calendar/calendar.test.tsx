/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { act, cleanup, render, screen } from "@testing-library/react";
import type { KeyboardEvent } from "react";
import userEvent from "@testing-library/user-event";
import { pl } from "date-fns/locale";
import type { Locale } from "date-fns";
import type { CalendarLabels } from "@makeplane/propel/components/calendar";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setLanguage } from "@plane/i18n";
import { Calendar } from "./calendar";

// These run against the real translations.

const JUNE_15 = new Date(2025, 5, 15);

function renderCalendar(
  extra: { locale?: Locale; labels?: CalendarLabels; onParentKeyDown?: (event: KeyboardEvent) => void } = {}
) {
  const { onParentKeyDown, ...calendarProps } = extra;
  return render(
    <div onKeyDown={onParentKeyDown}>
      <Calendar
        mode="single"
        defaultMonth={JUNE_15}
        today={JUNE_15}
        selected={new Date(2025, 5, 16)}
        onSelect={() => {}}
        {...calendarProps}
      />
    </div>
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

describe("Calendar keys", () => {
  const monthView = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(screen.getByRole("button", { name: "Choose the month, June" }));
  };
  const yearView = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(screen.getByRole("button", { name: "Choose the year, 2025" }));
  };

  describe("Escape", () => {
    it("steps back from the month view to the day view and does not reach what is around the calendar", async () => {
      const user = userEvent.setup();
      const onParentKeyDown = vi.fn();
      renderCalendar({ onParentKeyDown });
      await monthView(user);
      expect(screen.getByRole("group", { name: "Choose month for 2025" })).toBeDefined();
      onParentKeyDown.mockClear();

      await user.keyboard("{Escape}");

      expect(screen.queryByRole("group")).toBeNull();
      expect(screen.getByRole("grid")).toBeDefined();
      expect(onParentKeyDown).not.toHaveBeenCalled();
    });

    it("steps back from the year view too", async () => {
      const user = userEvent.setup();
      renderCalendar();
      await yearView(user);
      expect(screen.getByRole("group", { name: "Choose year from 2020 to 2031" })).toBeDefined();

      await user.keyboard("{Escape}");

      expect(screen.getByRole("grid")).toBeDefined();
    });

    it("keeps the month that was showing", async () => {
      const user = userEvent.setup();
      renderCalendar();
      await user.click(screen.getByRole("button", { name: "Next month" }));
      await user.click(screen.getByRole("button", { name: "Choose the month, July" }));

      await user.keyboard("{Escape}");

      expect(screen.getByRole("button", { name: "Choose the month, July" })).toBeDefined();
      expect(screen.getByRole("grid", { name: "July 2025" })).toBeDefined();
    });

    it("puts focus on the header, not on nothing", async () => {
      const user = userEvent.setup();
      renderCalendar();
      await monthView(user);

      await user.keyboard("{Escape}");

      expect((document.activeElement as HTMLElement).getAttribute("aria-label")).toBe("Choose the month, June");
    });

    it("is left to whatever is around the calendar in the day view", async () => {
      const user = userEvent.setup();
      const onParentKeyDown = vi.fn();
      renderCalendar({ onParentKeyDown });
      screen.getByRole("button", { name: "Monday, June 16th, 2025, selected" }).focus();

      await user.keyboard("{Escape}");

      expect(onParentKeyDown).toHaveBeenCalled();
    });
  });

  describe("PageUp and PageDown", () => {
    it("go to the next and previous year in the month view", async () => {
      const user = userEvent.setup();
      renderCalendar();
      await monthView(user);

      await user.keyboard("{PageDown}");
      expect(screen.getByRole("group", { name: "Choose month for 2026" })).toBeDefined();

      await user.keyboard("{PageUp}{PageUp}");
      expect(screen.getByRole("group", { name: "Choose month for 2024" })).toBeDefined();
    });

    it("go to the next and previous 12 years in the year view", async () => {
      const user = userEvent.setup();
      renderCalendar();
      await yearView(user);

      await user.keyboard("{PageDown}");
      expect(screen.getByRole("group", { name: "Choose year from 2032 to 2043" })).toBeDefined();

      await user.keyboard("{PageUp}{PageUp}");
      expect(screen.getByRole("group", { name: "Choose year from 2008 to 2019" })).toBeDefined();
    });

    it("keep focus on the same place of the page", async () => {
      const user = userEvent.setup();
      renderCalendar();
      await yearView(user);
      const before = (document.activeElement as HTMLElement).getAttribute("aria-label");
      expect(before).toBe("2025");

      await user.keyboard("{PageDown}");

      // 2025 is the sixth year of its page, so the sixth year of the next one
      expect((document.activeElement as HTMLElement).getAttribute("aria-label")).toBe("2037");
    });

    it("work in the interface language, where the arrows have other names", async () => {
      const user = userEvent.setup();
      await useLanguage("pl");
      renderCalendar({ locale: pl });
      await user.click(screen.getByRole("button", { name: "Wybierz rok, 2025" }));

      await user.keyboard("{PageDown}");

      expect(screen.getByRole("group", { name: "Wybierz rok od 2032 do 2043" })).toBeDefined();
    });

    it("do nothing when the arrow is disabled", async () => {
      const user = userEvent.setup();
      renderCalendar({ startMonth: new Date(2025, 0, 1), endMonth: new Date(2025, 11, 1) } as never);
      await monthView(user);

      await user.keyboard("{PageDown}");

      expect(screen.getByRole("group", { name: "Choose month for 2025" })).toBeDefined();
    });

    it("are left alone in the day view, where the grid has them", async () => {
      const user = userEvent.setup();
      renderCalendar();
      screen.getByRole("button", { name: "Monday, June 16th, 2025, selected" }).focus();

      await user.keyboard("{PageDown}");

      expect(screen.getByRole("button", { name: "Choose the month, July" })).toBeDefined();
    });
  });
});
