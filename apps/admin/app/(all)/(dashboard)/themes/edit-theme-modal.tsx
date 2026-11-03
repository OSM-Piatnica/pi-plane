/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { Input } from "@makeplane/propel/components/input";
import { setToast } from "@plane/blocks/toast";
import { InstanceService } from "@plane/services";
import type { TInstanceTheme, TInstanceThemeCreate } from "@plane/types";
import { toOverrideHex, validateHexColor } from "@plane/utils";
// local
import { getThemeErrorMessage, parseThemeFile } from "./theme-file";

type Props = {
  /** the theme being edited, or a theme read from a file that is not saved yet; the dialog is open while there is one */
  theme: TInstanceTheme | TInstanceThemeCreate | null;
  handleClose: () => void;
  onSaved: () => Promise<void>;
};

const instanceService = new InstanceService();

function ColorField(props: { id: string; label: string; value: string; onChange: (value: string) => void }) {
  const { id, label, value, onChange } = props;
  const isValid = validateHexColor(value);
  return (
    <div className="flex flex-col gap-1.5 text-body-sm-medium text-primary">
      <label htmlFor={id}>{label}</label>
      <span className="flex items-center gap-2">
        <span
          className="size-9 shrink-0 rounded-md border border-subtle-1"
          style={{ backgroundColor: isValid ? `#${value.replace("#", "")}` : "transparent" }}
        />
        <Input
          id={id}
          size="lg"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="#4F8F7D"
          aria-invalid={!isValid}
        />
      </span>
    </div>
  );
}

export function EditThemeModal(props: Props) {
  const { theme, handleClose, onSaved } = props;
  // refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  // states
  const [name, setName] = useState("");
  const [primary, setPrimary] = useState("");
  const [background, setBackground] = useState("");
  const [darkPalette, setDarkPalette] = useState(false);
  // the advanced colours are not edited here; a file can replace them
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);

  // start from the theme that is being edited
  useEffect(() => {
    if (!theme) return;
    setName(theme.name);
    setPrimary(theme.primary);
    setBackground(theme.background);
    setDarkPalette(theme.dark_palette);
    setOverrides(theme.overrides ?? {});
  }, [theme]);

  // a theme that comes from a file has no id yet: saving adds it
  const isNew = theme !== null && !("id" in theme);
  const canSave = name.trim().length > 0 && validateHexColor(primary) && validateHexColor(background) && !isSaving;

  const handleFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const parsed = await parseThemeFile(file);
      // the name stays as it is: the file only supplies the colours
      setPrimary(parsed.primary);
      setBackground(parsed.background);
      setDarkPalette(parsed.dark_palette);
      setOverrides(parsed.overrides);
    } catch (error) {
      setToast({ type: "error", title: "Could not read the file", message: getThemeErrorMessage(error) });
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSave = async () => {
    if (!theme) return;
    setIsSaving(true);
    try {
      const data = {
        name: name.trim(),
        primary: toOverrideHex(primary),
        background: toOverrideHex(background),
        dark_palette: darkPalette,
        overrides,
      };
      if ("id" in theme) await instanceService.updateTheme(theme.id, data);
      else await instanceService.createTheme(data);
      setToast({
        type: "success",
        title: isNew ? "Theme added" : "Theme updated",
        message: isNew ? `${data.name} is now in everybody's theme list.` : `${data.name} was saved.`,
      });
      await onSaved();
    } catch (error) {
      setToast({
        type: "error",
        title: isNew ? "Could not add the theme" : "Could not save the theme",
        message: getThemeErrorMessage(error),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open={Boolean(theme)}
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogContent size="sm">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>{isNew ? "Import theme" : "Edit theme"}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5 text-body-sm-medium text-primary">
                <label htmlFor="theme-name">Name</label>
                <Input id="theme-name" size="lg" value={name} onChange={(event) => setName(event.target.value)} />
              </div>
              <ColorField id="theme-primary" label="Primary colour" value={primary} onChange={setPrimary} />
              <ColorField id="theme-background" label="Background colour" value={background} onChange={setBackground} />
              <fieldset className="flex items-center gap-4 text-body-sm-regular text-primary">
                <legend className="mb-1.5 text-body-sm-medium">Colour mode</legend>
                <label className="flex items-center gap-1.5">
                  <input type="radio" name="theme-mode" checked={!darkPalette} onChange={() => setDarkPalette(false)} />
                  Light
                </label>
                <label className="flex items-center gap-1.5">
                  <input type="radio" name="theme-mode" checked={darkPalette} onChange={() => setDarkPalette(true)} />
                  Dark
                </label>
              </fieldset>
              <div className="flex items-center justify-between gap-3 rounded-md bg-layer-1 p-3 text-body-xs-regular text-secondary">
                <span>
                  {Object.keys(overrides).length} advanced colours. Load a theme config file to replace all of the
                  colours above and these.
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json,application/json"
                  className="hidden"
                  onChange={(event) => {
                    void handleFile(event);
                  }}
                />
                <Button
                  variant="secondary"
                  size="md"
                  stretch="auto"
                  label="Load from file"
                  onClick={() => fileInputRef.current?.click()}
                />
              </div>
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button variant="secondary" size="md" stretch="auto" onClick={handleClose} label="Cancel" />
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            loading={isSaving}
            disabled={!canSave}
            onClick={() => {
              void handleSave();
            }}
            label={isSaving ? "Saving" : isNew ? "Add theme" : "Save"}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
}
