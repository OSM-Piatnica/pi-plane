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
import type { TInstanceTheme, TInstanceThemeCreate } from "@plane/types";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// types
import type { Route } from "./+types/page";
// local
import { EditThemeModal } from "./edit-theme-modal";
import { getThemeErrorMessage, parseThemeFile } from "./theme-file";

const instanceService = new InstanceService();
const THEMES_KEY = "INSTANCE_THEMES";

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
  const [editingTheme, setEditingTheme] = useState<TInstanceTheme | TInstanceThemeCreate | null>(null);

  const { data: themes, mutate } = useSWR(THEMES_KEY, () => instanceService.themes());

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsWorking(true);
    try {
      // the name is up to the admin: the dialog opens with the one from the file, to change before adding
      setEditingTheme(await parseThemeFile(file));
    } catch (error) {
      setToast({ type: "error", title: "Could not read the file", message: getThemeErrorMessage(error) });
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
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="lg"
                    stretch="auto"
                    label="Edit"
                    disabled={isWorking}
                    onClick={() => setEditingTheme(theme)}
                  />
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
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
      <EditThemeModal
        theme={editingTheme}
        handleClose={() => setEditingTheme(null)}
        onSaved={async () => {
          await mutate();
          setEditingTheme(null);
        }}
      />
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Themes Settings - God Mode" }];

export default InstanceThemesPage;
