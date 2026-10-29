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
import type { TUserGroup, TUserGroupFormData } from "@plane/types";

type Props = {
  /** The group being edited; none when a group is created. */
  group?: TUserGroup | null;
  /** The parent of a new group. */
  parentId?: string | null;
  /** The groups a new group can be placed under: the ones the person manages. */
  parentOptions: TUserGroup[];
  /** Whether a group can be created without a parent (a workspace admin only). */
  canCreateTopLevel: boolean;
  onClose: () => void;
  onSubmit: (data: TUserGroupFormData) => Promise<void>;
};

export function GroupFormModal(props: Props) {
  const { group, parentId, parentOptions, canCreateTopLevel, onClose, onSubmit } = props;
  // translation
  const { t } = useTranslation();
  // states
  // The parent mounts a fresh modal for every group it opens, so the form starts from the group's own values
  const [name, setName] = useState(group?.name ?? "");
  const [description, setDescription] = useState(group?.description ?? "");
  const [parent, setParent] = useState<string>(group ? (group.parent ?? "") : (parentId ?? ""));
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditing = Boolean(group);
  const canSubmit = name.trim().length > 0 && (isEditing || canCreateTopLevel || parent !== "");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim(),
        ...(isEditing ? {} : { parent: parent || null }),
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
                <DialogTitle>
                  {isEditing
                    ? t("workspace_settings.settings.groups.edit_group")
                    : t("workspace_settings.settings.groups.create_group")}
                </DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-4">
                <div>
                  <label htmlFor="user-group-name" className="text-13 text-secondary">
                    {t("workspace_settings.settings.groups.name")}
                  </label>
                  <InputGroup size="2xl">
                    <Input
                      size="2xl"
                      id="user-group-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      maxLength={255}
                      autoComplete="off"
                    />
                  </InputGroup>
                </div>
                <div>
                  <label htmlFor="user-group-description" className="text-13 text-secondary">
                    {t("workspace_settings.settings.groups.description_label")}
                  </label>
                  <InputGroup size="2xl">
                    <Input
                      size="2xl"
                      id="user-group-description"
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      autoComplete="off"
                    />
                  </InputGroup>
                </div>
                {!isEditing && (
                  <div>
                    <label htmlFor="user-group-parent" className="text-13 text-secondary">
                      {t("workspace_settings.settings.groups.parent")}
                    </label>
                    <select
                      id="user-group-parent"
                      value={parent}
                      onChange={(event) => setParent(event.target.value)}
                      className="mt-1 h-10 w-full rounded-md border border-subtle bg-surface-1 px-3 text-13 text-primary"
                    >
                      {canCreateTopLevel && (
                        <option value="">{t("workspace_settings.settings.groups.top_level")}</option>
                      )}
                      {parentOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
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
                label={isEditing ? t("save") : t("workspace_settings.settings.groups.create")}
              />
            </DialogActions>
          </DialogMain>
        </form>
      </DialogContent>
    </Dialog>
  );
}
