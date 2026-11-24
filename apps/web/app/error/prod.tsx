/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
import { useTheme } from "next-themes";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { useTranslation } from "@plane/i18n";
// assets
import maintenanceModeDarkModeImage from "@/app/assets/instance/maintenance-mode-dark.svg?url";
import maintenanceModeLightModeImage from "@/app/assets/instance/maintenance-mode-light.svg?url";
// layouts
import DefaultLayout from "@/layouts/default-layout";

// Where people can report a problem. The support contact of the organisation is still to be decided (TBD):
// until then this goes to the issues of the project, as the page always did.
const SUPPORT_URL = "https://github.com/OSM-Piatnica/pi-plane/issues";

// Shown when translations are not available, which is a likely reason to be on this page at all
// (the key itself would come back from `t`).
const FALLBACK_TEXT = {
  title: "Looks like something went wrong!",
  description:
    "Something went wrong while showing this page. Refresh the page or go back to the home page. If the problem continues, please contact support.",
  contactSupport: "Contact Support",
  refresh: "Refresh",
  goHome: "Go to Home",
};

const KEYS = {
  title: "app_text.error_page.title",
  description: "app_text.error_page.description",
  contactSupport: "app_text.error_page.contact_support",
  refresh: "refresh",
  goHome: "app_text.not_found.go_to_home",
} as const;

// Production Error Component
interface ProdErrorComponentProps {
  onGoHome: () => void;
  onReload: () => void;
}

export function ProdErrorComponent({ onGoHome, onReload }: ProdErrorComponentProps) {
  // hooks
  const { resolvedTheme } = useTheme();
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);

  // derived values
  const maintenanceModeImage = resolvedTheme === "dark" ? maintenanceModeDarkModeImage : maintenanceModeLightModeImage;
  const text = (name: keyof typeof KEYS) => {
    const translated = t(KEYS[name]);
    return translated === KEYS[name] ? FALLBACK_TEXT[name] : translated;
  };

  // A screen reader user lands here without having asked to: move the focus to the main action
  useEffect(() => {
    containerRef.current?.querySelector("button")?.focus();
  }, []);

  return (
    <DefaultLayout>
      <div
        ref={containerRef}
        role="alert"
        className="relative container mx-auto flex h-full w-full max-w-xl flex-col items-center justify-center gap-2 gap-y-6 bg-surface-1 px-6 text-center"
      >
        <div className="relative w-full">
          <img
            src={maintenanceModeImage}
            height="176"
            width="288"
            alt=""
            aria-hidden="true"
            className="h-full w-full object-contain object-center"
          />
        </div>
        <div className="relative mt-4 flex w-full flex-col items-center gap-4">
          <div className="flex flex-col gap-2.5">
            <h1 className="text-18 font-semibold text-primary">
              <span aria-hidden="true">&#x1F6A7;</span> {text("title")}
            </h1>
            <p className="text-14 font-medium text-secondary">{text("description")}</p>
          </div>

          <div className="flex items-center justify-center gap-3">
            <Button variant="primary" size="md" stretch="auto" label={text("refresh")} onClick={onReload} />
            <Button variant="secondary" size="md" stretch="auto" label={text("goHome")} onClick={onGoHome} />
          </div>

          <a
            href={SUPPORT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-13 text-accent-primary hover:underline"
          >
            {text("contactSupport")}
          </a>
        </div>
      </div>
    </DefaultLayout>
  );
}
