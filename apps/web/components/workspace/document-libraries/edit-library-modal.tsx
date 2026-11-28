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
import type { TDocumentLibrary, TDocumentLibraryUpdate } from "@plane/types";
// helpers
import { DOCUMENT_LIBRARY_NAME_MAX_LENGTH, normalizeFolderPath } from "@/helpers/document-library";

type Props = {
  library: TDocumentLibrary;
  onClose: () => void;
  onSubmit: (data: TDocumentLibraryUpdate) => Promise<void>;
};

const T = "workspace_settings.settings.document_libraries";

export function EditDocumentLibraryModal(props: Props) {
  const { library, onClose, onSubmit } = props;
  // translation
  const { t } = useTranslation();
  // states (the parent mounts a fresh modal for every library it opens)
  const [name, setName] = useState(library.name);
  const [rootPath, setRootPath] = useState(library.root_path);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const normalizedRoot = normalizeFolderPath(rootPath);
  const canSubmit = normalizedRoot !== null && !isSubmitting;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (normalizedRoot === null) return;
    setIsSubmitting(true);
    try {
      await onSubmit({ name: name.trim(), root_path: normalizedRoot });
      onClose();
    } catch {
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
                <DialogTitle>{t(`${T}.edit`)}</DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-4">
                <div>
                  <label htmlFor="document-library-edit-name" className="text-13 text-secondary">
                    {t(`${T}.name`)}
                  </label>
                  <InputGroup size="2xl">
                    <Input
                      size="2xl"
                      id="document-library-edit-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      maxLength={DOCUMENT_LIBRARY_NAME_MAX_LENGTH}
                      autoComplete="off"
                    />
                  </InputGroup>
                </div>
                <div>
                  <label htmlFor="document-library-edit-root" className="text-13 text-secondary">
                    {t(`${T}.root_folder`)}
                  </label>
                  <InputGroup size="2xl">
                    <Input
                      size="2xl"
                      id="document-library-edit-root"
                      value={rootPath}
                      onChange={(event) => setRootPath(event.target.value)}
                      autoComplete="off"
                    />
                  </InputGroup>
                  <p className="pt-1 text-11 text-tertiary">{t(`${T}.root_folder_change_hint`)}</p>
                  {normalizedRoot === null && (
                    <p role="alert" className="pt-1 text-11 text-danger-primary">
                      {t(`${T}.errors.invalid_folder`)}
                    </p>
                  )}
                </div>
              </div>
            </DialogBody>
            <DialogActions>
              <Button
                size="md"
                stretch="auto"
                type="button"
                variant="secondary"
                onClick={onClose}
                label={t("cancel")}
              />
              <Button
                size="md"
                stretch="auto"
                type="submit"
                variant="primary"
                loading={isSubmitting}
                disabled={!canSubmit}
                label={t("save")}
              />
            </DialogActions>
          </DialogMain>
        </form>
      </DialogContent>
    </Dialog>
  );
}
