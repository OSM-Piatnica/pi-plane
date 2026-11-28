/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
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
import { Input, InputGroup } from "@makeplane/propel/components/input";
import type { TDocumentLibraryCreate, TDocumentSite } from "@plane/types";
// helpers
import {
  DOCUMENT_LIBRARY_NAME_MAX_LENGTH,
  getDocumentLibraryErrorMessage,
  isSharePointSiteUrl,
  normalizeFolderPath,
} from "@/helpers/document-library";
// services
import { documentLibraryService } from "@/services/document-library.service";

type Props = {
  workspaceSlug: string;
  onClose: () => void;
  /** Adds the library; throws (and shows what went wrong) when it cannot. */
  onSubmit: (data: TDocumentLibraryCreate) => Promise<void>;
};

const T = "workspace_settings.settings.document_libraries";

/** Why the root folder cannot be used: not a valid folder, or this folder of the library is already added. */
const getRootFolderError = (root: string | null, usedRootPaths: string[]) => {
  if (root === null) return "invalid_folder";
  return usedRootPaths.includes(root) ? "library_exists" : null;
};

export function AddDocumentLibraryModal(props: Props) {
  const { workspaceSlug, onClose, onSubmit } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [siteUrl, setSiteUrl] = useState("");
  const [site, setSite] = useState<TDocumentSite | null>(null);
  const [driveId, setDriveId] = useState("");
  const [name, setName] = useState("");
  const [rootPath, setRootPath] = useState("");
  const [makeDefault, setMakeDefault] = useState(false);
  const [lookupError, setLookupError] = useState("");
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // derived values
  const drive = site?.drives.find((item) => item.id === driveId);
  const normalizedRoot = normalizeFolderPath(rootPath);
  const rootError = getRootFolderError(normalizedRoot, drive?.used_root_paths ?? []);
  const canSubmit = drive !== undefined && rootError === null && !isSubmitting;

  const handleLookUp = async () => {
    setLookupError("");
    if (!isSharePointSiteUrl(siteUrl)) {
      setLookupError(t(`${T}.errors.invalid_site_url`));
      return;
    }
    setIsLookingUp(true);
    try {
      const found = await documentLibraryService.lookUpSite(workspaceSlug, siteUrl.trim());
      setSite(found);
      const first = found.drives[0];
      setDriveId(first?.id ?? "");
      setName(first?.name ?? "");
    } catch (error) {
      setSite(null);
      setLookupError(getDocumentLibraryErrorMessage(error, t, t("something_went_wrong_please_try_again")));
    } finally {
      setIsLookingUp(false);
    }
  };

  const handlePickDrive = (id: string) => {
    const picked = site?.drives.find((item) => item.id === id);
    // The name follows the library until the person types their own
    if (picked && (name === "" || site?.drives.some((item) => item.name === name))) setName(picked.name);
    setDriveId(id);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit || normalizedRoot === null) return;
    setIsSubmitting(true);
    try {
      await onSubmit({
        site_url: siteUrl.trim(),
        drive_id: driveId,
        name: name.trim(),
        root_path: normalizedRoot,
        is_default: makeDefault,
      });
      onClose();
    } catch {
      // the caller shows what went wrong; the dialog stays open for another try
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="lg">
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>{t(`${T}.add`)}</DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-4">
                <div>
                  <label htmlFor="document-library-site" className="text-13 text-secondary">
                    {t(`${T}.site_url`)}
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <InputGroup size="2xl">
                        <Input
                          size="2xl"
                          id="document-library-site"
                          value={siteUrl}
                          onChange={(event) => {
                            setSiteUrl(event.target.value);
                            setSite(null);
                          }}
                          placeholder="https://contoso.sharepoint.com/sites/Projects"
                          autoComplete="off"
                        />
                      </InputGroup>
                    </div>
                    <Button
                      size="md"
                      stretch="auto"
                      variant="secondary"
                      type="button"
                      disabled={!siteUrl.trim() || isLookingUp}
                      onClick={() => void handleLookUp()}
                      loading={isLookingUp}
                      label={t(`${T}.look_up`)}
                    />
                  </div>
                  <p className="pt-1 text-11 text-tertiary">{t(`${T}.site_url_hint`)}</p>
                  {lookupError && (
                    <p role="alert" className="pt-1 text-11 text-danger-primary">
                      {lookupError}
                    </p>
                  )}
                </div>

                {site && <SiteDrivePicker site={site} driveId={driveId} onPick={handlePickDrive} />}

                {drive && (
                  <>
                    <div>
                      <label htmlFor="document-library-name" className="text-13 text-secondary">
                        {t(`${T}.name`)}
                      </label>
                      <InputGroup size="2xl">
                        <Input
                          size="2xl"
                          id="document-library-name"
                          value={name}
                          onChange={(event) => setName(event.target.value)}
                          maxLength={DOCUMENT_LIBRARY_NAME_MAX_LENGTH}
                          autoComplete="off"
                        />
                      </InputGroup>
                    </div>
                    <div>
                      <label htmlFor="document-library-root" className="text-13 text-secondary">
                        {t(`${T}.root_folder`)}
                      </label>
                      <InputGroup size="2xl">
                        <Input
                          size="2xl"
                          id="document-library-root"
                          value={rootPath}
                          onChange={(event) => setRootPath(event.target.value)}
                          placeholder="Pi-Plane"
                          autoComplete="off"
                        />
                      </InputGroup>
                      <p className="pt-1 text-11 text-tertiary">{t(`${T}.root_folder_hint`)}</p>
                      {rootError && (
                        <p role="alert" className="pt-1 text-11 text-danger-primary">
                          {t(`${T}.errors.${rootError}`)}
                        </p>
                      )}
                    </div>
                    <label className="flex items-center gap-2 text-13 text-primary">
                      <input
                        type="checkbox"
                        checked={makeDefault}
                        onChange={(event) => setMakeDefault(event.target.checked)}
                      />
                      {t(`${T}.make_default_on_add`)}
                    </label>
                  </>
                )}
              </div>
            </DialogBody>
            <DialogActions>
              <Button
                size="md"
                stretch="auto"
                variant="secondary"
                type="button"
                onClick={onClose}
                label={t("cancel")}
              />
              <Button
                size="md"
                stretch="auto"
                variant="primary"
                type="submit"
                loading={isSubmitting}
                disabled={!canSubmit}
                label={t(`${T}.add`)}
              />
            </DialogActions>
          </DialogMain>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** The document libraries of a looked-up site, one to pick. */
function SiteDrivePicker(props: { site: TDocumentSite; driveId: string; onPick: (driveId: string) => void }) {
  const { site, driveId, onPick } = props;
  const { t } = useTranslation();
  if (site.drives.length === 0) {
    return <p className="text-13 text-secondary">{t(`${T}.no_drives`, { site: site.site.name })}</p>;
  }
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="pb-1 text-13 text-secondary">{t(`${T}.pick_drive`, { site: site.site.name })}</legend>
      {site.drives.map((item) => (
        <label
          key={item.id}
          className="flex cursor-pointer items-start gap-2 rounded-md border border-subtle px-3 py-2"
        >
          <input
            type="radio"
            name="document-library-drive"
            value={item.id}
            checked={item.id === driveId}
            onChange={() => onPick(item.id)}
            className="mt-1"
          />
          <span className="min-w-0">
            <span className="block truncate text-14 text-primary">{item.name}</span>
            {item.used_root_paths.length > 0 && (
              <span className="block text-11 text-tertiary">
                {t(`${T}.already_added`, { folders: item.used_root_paths.map((path) => path || "/").join(", ") })}
              </span>
            )}
          </span>
        </label>
      ))}
    </fieldset>
  );
}
