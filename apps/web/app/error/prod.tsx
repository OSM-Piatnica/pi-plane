/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { useTranslation } from "@plane/i18n";
// assets
import maintenanceModeDarkModeImage from "@/app/assets/instance/maintenance-mode-dark.svg?url";
import maintenanceModeLightModeImage from "@/app/assets/instance/maintenance-mode-light.svg?url";
// layouts
import DefaultLayout from "@/layouts/default-layout";
// local imports
import { buildErrorDetails, createErrorReference } from "./error-details";
import { getErrorKind } from "./error-kind";
import type { TErrorKind } from "./error-kind";

// Where people can report a problem. The support contact of the organisation is still to be decided (TBD):
// until then this goes to the issues of the project, as the page always did.
const SUPPORT_URL = "https://github.com/OSM-Piatnica/pi-plane/issues";

// Shown when translations are not available, which is a likely reason to be on this page at all
// (the key itself would come back from `t`).
const FALLBACK_TEXT: Record<string, string> = {
  "app_text.error_page.title": "Looks like something went wrong!",
  "app_text.error_page.description":
    "Something went wrong while showing this page. Refresh the page or go back to the home page. If the problem continues, please contact support.",
  "app_text.error_page.contact_support": "Contact Support",
  "app_text.error_page.kind.offline.title": "You appear to be offline",
  "app_text.error_page.kind.offline.description": "Check your internet connection, then refresh the page.",
  "app_text.error_page.kind.access.title": "You don't have access to this page",
  "app_text.error_page.kind.access.description":
    "Your account is not allowed to open this page. Ask a workspace admin for access, or go back to the home page.",
  "app_text.error_page.kind.server.title": "The server could not answer",
  "app_text.error_page.kind.server.description":
    "The server had a problem with your request. Try again in a moment. If it keeps happening, please contact support.",
  "app_text.error_page.kind.not_found.title": "This page could not be found",
  "app_text.not_found.description":
    "Sorry, the page you are looking for cannot be found. It may have been removed, had its name changed, or is temporarily unavailable.",
  "app_text.error_page.reference": "Reference: {reference}",
  "app_text.error_page.copy_details": "Copy details",
  "common.copied": "Copied!",
  refresh: "Refresh",
  "app_text.not_found.go_to_home": "Go to Home",
};

// The title and description of each kind of failure; a generic failure and a missing page share text with others
const KIND_KEYS: Record<TErrorKind, { title: string; description: string }> = {
  generic: { title: "app_text.error_page.title", description: "app_text.error_page.description" },
  offline: {
    title: "app_text.error_page.kind.offline.title",
    description: "app_text.error_page.kind.offline.description",
  },
  access: {
    title: "app_text.error_page.kind.access.title",
    description: "app_text.error_page.kind.access.description",
  },
  server: {
    title: "app_text.error_page.kind.server.title",
    description: "app_text.error_page.kind.server.description",
  },
  not_found: { title: "app_text.error_page.kind.not_found.title", description: "app_text.not_found.description" },
};

// Production Error Component
interface ProdErrorComponentProps {
  error: unknown;
  onGoHome: () => void;
  onReload: () => void;
}

export function ProdErrorComponent({ error, onGoHome, onReload }: ProdErrorComponentProps) {
  // hooks
  const { resolvedTheme } = useTheme();
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  // the reference and the details are made once, when the page appears
  const [reference] = useState(createErrorReference);
  const [kind] = useState(() => getErrorKind(error));
  const [details] = useState(() =>
    buildErrorDetails({
      reference,
      kind,
      error,
      path: typeof window === "undefined" ? "/" : window.location.pathname,
      time: new Date(),
    })
  );
  const [isCopied, setIsCopied] = useState(false);

  // derived values
  const maintenanceModeImage = resolvedTheme === "dark" ? maintenanceModeDarkModeImage : maintenanceModeLightModeImage;
  const canCopy = typeof navigator !== "undefined" && Boolean(navigator.clipboard?.writeText);
  const text = (key: string, params?: Record<string, string>) => {
    const translated = t(key, params);
    if (translated !== key) return translated;
    return (FALLBACK_TEXT[key] ?? key).replace(/\{(\w+)\}/g, (_, name: string) => params?.[name] ?? "");
  };

  // A screen reader user lands here without having asked to: move the focus to the main action
  useEffect(() => {
    containerRef.current?.querySelector("button")?.focus();
  }, []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(details);
      setIsCopied(true);
      window.setTimeout(() => setIsCopied(false), 2000);
    } catch {
      // nothing to tell the person: the reference is on the page to read out
    }
  };

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
              <span aria-hidden="true">&#x1F6A7;</span> {text(KIND_KEYS[kind].title)}
            </h1>
            <p className="text-14 font-medium text-secondary">{text(KIND_KEYS[kind].description)}</p>
          </div>

          <div className="flex items-center justify-center gap-3">
            <Button variant="primary" size="md" stretch="auto" label={text("refresh")} onClick={onReload} />
            <Button
              variant="secondary"
              size="md"
              stretch="auto"
              label={text("app_text.not_found.go_to_home")}
              onClick={onGoHome}
            />
          </div>

          <div className="flex flex-col items-center gap-1.5 text-12 text-tertiary">
            <span>{text("app_text.error_page.reference", { reference })}</span>
            {canCopy && (
              <button type="button" className="text-accent-primary hover:underline" onClick={() => void handleCopy()}>
                {isCopied ? text("common.copied") : text("app_text.error_page.copy_details")}
              </button>
            )}
          </div>

          <a
            href={SUPPORT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-13 text-accent-primary hover:underline"
          >
            {text("app_text.error_page.contact_support")}
          </a>
        </div>
      </div>
    </DefaultLayout>
  );
}
