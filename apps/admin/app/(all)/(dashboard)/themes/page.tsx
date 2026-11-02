/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import { InstanceService } from "@plane/services";
import type { TInstanceTheme } from "@plane/types";
import { sanitizeThemeOverrides, toOverrideHex, validateHexColor } from "@plane/utils";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// types
import type { Route } from "./+types/page";

const instanceService = new InstanceService();
const THEMES_KEY = "INSTANCE_THEMES";

/** Reads a theme file: the config the app exports from Appearance (`themeName`, `primary`, `background`, ...). */
const parseThemeFile = async (file: File) => {
  const raw = JSON.parse(await file.text()) as Record<string, unknown>;
  const primary = String(raw.primary ?? "");
  const background = String(raw.background ?? "");
  if (!validateHexColor(primary) || !validateHexColor(background)) {
    throw new Error("The file needs a primary and a background colour, written as hex codes like #4F8F7D.");
  }
  const { overrides, invalid } = sanitizeThemeOverrides(raw.overrides);
  if (invalid.length > 0) throw new Error(`These colours are not hex codes: ${invalid.join(", ")}.`);
  const name = String(raw.themeName ?? raw.name ?? file.name.replace(/\.json$/i, "")).trim();
  return {
    name,
    primary: toOverrideHex(primary),
    background: toOverrideHex(background),
    dark_palette: raw.darkPalette === true,
    overrides,
  };
};

function ThemeSwatches({ theme }: { theme: TInstanceTheme }) {
  const colors = {
    primary: theme.primary,
    background: theme.background,
    surface: theme.overrides["bg-surface-1"],
    text: theme.overrides["txt-primary"],
  };
  return (
    <div className="flex">
      {Object.entries(colors).map(([role, color]) =>
        color ? (
          <span
            key={role}
            className="-ml-1 size-5 rounded-full border border-subtle first:ml-0"
            style={{ backgroundColor: color }}
          />
        ) : null
      )}
    </div>
  );
}

const InstanceThemesPage = observer(function InstanceThemesPage(_props: Route.ComponentProps) {
  // refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  // states
  const [isWorking, setIsWorking] = useState(false);

  const { data: themes, mutate } = useSWR(THEMES_KEY, () => instanceService.themes());

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsWorking(true);
    try {
      const theme = await parseThemeFile(file);
      await instanceService.createTheme(theme);
      await mutate();
      setToast({ type: "success", title: "Theme added", message: `${theme.name} is now in everybody's theme list.` });
    } catch (error) {
      const apiError = error as Record<string, string> | Error;
      setToast({
        type: "error",
        title: "Could not add the theme",
        message:
          apiError instanceof Error
            ? apiError.message
            : (Object.values(apiError).find((value) => typeof value === "string") ?? "Something went wrong."),
      });
    } finally {
      setIsWorking(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (theme: TInstanceTheme) => {
    setIsWorking(true);
    try {
      await instanceService.deleteTheme(theme.id);
      await mutate();
      setToast({ type: "success", title: "Theme deleted", message: `${theme.name} was removed.` });
    } catch {
      setToast({ type: "error", title: "Could not delete the theme", message: "Something went wrong." });
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <PageWrapper
      header={{
        title: "Themes for everyone on this instance",
        description:
          "Themes added here show up in every user's theme list. Import a theme config exported from Appearance. Themes loaded by the deployment are read-only.",
      }}
    >
      <div className="space-y-4">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          className="hidden"
          onChange={(event) => {
            void handleImport(event);
          }}
        />
        <Button
          variant="primary"
          size="lg"
          stretch="auto"
          label="Import theme"
          disabled={isWorking}
          onClick={() => fileInputRef.current?.click()}
        />
        {themes && themes.length === 0 && <p className="text-13 text-secondary">No extra themes yet.</p>}
        <ul className="divide-y divide-subtle rounded-lg border border-subtle">
          {(themes ?? []).map((theme) => (
            <li key={theme.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <ThemeSwatches theme={theme} />
                <span className="truncate text-body-sm-medium text-primary">{theme.name}</span>
                <span className="text-body-xs-regular text-secondary">{theme.dark_palette ? "Dark" : "Light"}</span>
              </div>
              {theme.is_read_only ? (
                <span className="text-body-xs-regular text-secondary">Set by the deployment</span>
              ) : (
                <Button
                  variant="secondary"
                  size="lg"
                  stretch="auto"
                  label="Delete"
                  disabled={isWorking}
                  onClick={() => {
                    void handleDelete(theme);
                  }}
                />
              )}
            </li>
          ))}
        </ul>
      </div>
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Themes Settings - God Mode" }];

export default InstanceThemesPage;
