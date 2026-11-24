/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

// `t` of the test: either returns the key (as when translations are missing) or looks the key up
const translations: { value: Record<string, string> | null } = { value: null };

vi.mock("@plane/i18n", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) => {
      const text = translations.value?.[key];
      if (!text) return key;
      return text.replace(/\{(\w+)\}/g, (_, name: string) => params?.[name] ?? "");
    },
  }),
}));
vi.mock("next-themes", () => ({ useTheme: () => ({ resolvedTheme: "light" }) }));
vi.mock("@/layouts/default-layout", () => ({ default: ({ children }: { children: unknown }) => children }));
vi.mock("@/app/assets/instance/maintenance-mode-dark.svg?url", () => ({ default: "dark.svg" }));
vi.mock("@/app/assets/instance/maintenance-mode-light.svg?url", () => ({ default: "light.svg" }));

const { ProdErrorComponent } = await import("../../app/error/prod");

const render = (error: unknown) =>
  renderToStaticMarkup(<ProdErrorComponent error={error} onGoHome={() => undefined} onReload={() => undefined} />);

describe("ProdErrorComponent", () => {
  it("shows English text when translations are not available, never raw keys", () => {
    translations.value = null;
    const html = render(new Error("boom"));
    expect(html).toContain("Looks like something went wrong!");
    expect(html).toContain("If the problem continues, please contact support.");
    expect(html).toContain(">Refresh<");
    expect(html).toContain(">Go to Home<");
    expect(html).toContain(">Contact Support<");
    expect(html).not.toMatch(/app_text\.|>refresh</);
  });

  it("has a role alert, a decorative image and links only to the project's issues", () => {
    translations.value = null;
    const html = render(new Error("boom"));
    expect(html).toContain('role="alert"');
    expect(html).toContain('alt=""');
    expect(html).not.toContain("plane.so");
    expect(html).not.toContain("planepowers");
    expect([...html.matchAll(/<a [^>]*href="([^"]+)"/g)].map((match) => match[1])).toEqual([
      "https://github.com/OSM-Piatnica/pi-plane/issues",
    ]);
  });

  it("shows a reference of the form XXXX-XXXX", () => {
    translations.value = null;
    expect(render(new Error("boom"))).toMatch(/Reference: [A-HJKMNP-Z2-9]{4}-[A-HJKMNP-Z2-9]{4}/);
  });

  it("says what kind of failure it is", () => {
    translations.value = null;
    expect(render({ response: { status: 403 } })).toContain("You don&#x27;t have access to this page");
    expect(render({ response: { status: 502 } })).toContain("The server could not answer");
    expect(render({ status: 404 })).toContain("This page could not be found");
  });

  it("uses the translation when there is one", () => {
    translations.value = {
      "app_text.error_page.title": "Hier ist leider etwas schiefgelaufen!",
      refresh: "Aktualisieren",
    };
    const html = render(new Error("boom"));
    expect(html).toContain("Hier ist leider etwas schiefgelaufen!");
    expect(html).toContain(">Aktualisieren<");
    // a key without a translation still falls back to English
    expect(html).toContain(">Go to Home<");
  });
});
