/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
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
import { Field } from "@makeplane/propel/components/field";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { useTranslation } from "@plane/i18n";

const MAX_NAME_LENGTH = 255;

type TNameDialogProps = {
  title: string;
  description?: string;
  initialName: string;
  onClose: () => void;
  /** Resolves when the name was taken; a rejection keeps the dialog open. */
  onSubmit: (name: string) => Promise<void>;
};

/**
 * Asks for the name of a baseline, to save a new one or to rename one. Render it only while it is open: the name
 * field starts from `initialName` each time.
 */
export function BaselineNameDialog(props: TNameDialogProps) {
  const { title, description, initialName, onClose, onSubmit } = props;
  const { t } = useTranslation();
  const [name, setName] = useState(initialName);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const trimmedName = name.trim();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!trimmedName || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onSubmit(trimmedName);
      onClose();
    } catch {
      // the caller has said what went wrong; the name stays to be tried again
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !isSubmitting) onClose();
      }}
    >
      <DialogContent size="md">
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>{title}</DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody tabIndex={0}>
              <div className="space-y-3">
                {description && <p className="text-13 text-secondary">{description}</p>}
                <div>
                  <label htmlFor="baseline-name" className="mb-2 block text-14 font-medium text-secondary">
                    {t("name")}
                  </label>
                  <Field name="baseline-name" invalid={!trimmedName}>
                    <InputGroup size="2xl">
                      <Input
                        size="2xl"
                        id="baseline-name"
                        type="text"
                        value={name}
                        maxLength={MAX_NAME_LENGTH}
                        onChange={(event) => setName(event.target.value)}
                        data-testid="baseline-name-input"
                      />
                    </InputGroup>
                  </Field>
                </div>
              </div>
            </DialogBody>
          </DialogMain>
          <DialogActions>
            <Button
              variant="secondary"
              size="md"
              stretch="auto"
              onClick={onClose}
              disabled={isSubmitting}
              label={t("cancel")}
            />
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              type="submit"
              loading={isSubmitting}
              disabled={!trimmedName}
              label={t("save")}
            />
          </DialogActions>
        </form>
      </DialogContent>
    </Dialog>
  );
}

type TDeleteDialogProps = {
  name: string;
  onClose: () => void;
  /** Resolves when the baseline is gone; a rejection keeps the dialog open. */
  onConfirm: () => Promise<void>;
};

/** Confirms deleting a baseline. Render it only while it is open. */
export function BaselineDeleteDialog(props: TDeleteDialogProps) {
  const { name, onClose, onConfirm } = props;
  const { t } = useTranslation();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleConfirm = async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    try {
      await onConfirm();
      onClose();
    } catch {
      setIsDeleting(false);
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !isDeleting) onClose();
      }}
    >
      <DialogContent size="md">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>{t("baseline.delete_title")}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody tabIndex={0}>
            <p className="text-14 text-secondary">{t("baseline.delete_confirm", { name })}</p>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            onClick={onClose}
            disabled={isDeleting}
            label={t("cancel")}
          />
          <Button
            variant="danger"
            size="md"
            stretch="auto"
            onClick={handleConfirm}
            loading={isDeleting}
            label={t("delete")}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
}
