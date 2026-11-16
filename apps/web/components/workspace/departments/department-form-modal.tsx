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
// helpers
import {
  DEPARTMENT_CODE_MAX_LENGTH,
  DEPARTMENT_COLORS,
  DEPARTMENT_NAME_MAX_LENGTH,
  isDepartmentColor,
  normalizeDepartmentCode,
} from "@/helpers/department";

type Props = {
  /** The department being edited; none when one is added. */
  department?: TUserGroup | null;
  onClose: () => void;
  /** The name is left out for a department whose name the identity provider owns. */
  onSubmit: (data: Partial<TUserGroupFormData>) => Promise<void>;
};

export function DepartmentFormModal(props: Props) {
  const { department, onClose, onSubmit } = props;
  // translation
  const { t } = useTranslation();
  // states
  // The parent mounts a fresh modal for every department it opens, so the form starts from its own values
  const [name, setName] = useState(department?.name ?? "");
  const [code, setCode] = useState(department?.code ?? "");
  const [color, setColor] = useState(department?.color ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditing = Boolean(department);
  // The provider owns the name of a department it manages
  const isNameLocked = Boolean(department?.is_external);
  const canSubmit = name.trim().length > 0 && isDepartmentColor(color.trim());

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      const data: Partial<TUserGroupFormData> = { code: normalizeDepartmentCode(code), color: color.trim() };
      if (!isNameLocked) data.name = name.trim();
      if (!isEditing) data.kind = "department";
      await onSubmit(data);
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
                    ? t("workspace_settings.settings.departments.edit")
                    : t("workspace_settings.settings.departments.add")}
                </DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-4">
                <div>
                  <label htmlFor="department-name" className="text-13 text-secondary">
                    {t("workspace_settings.settings.groups.name")}
                  </label>
                  <InputGroup size="2xl">
                    <Input
                      size="2xl"
                      id="department-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      maxLength={DEPARTMENT_NAME_MAX_LENGTH}
                      autoComplete="off"
                      disabled={isNameLocked}
                    />
                  </InputGroup>
                  {isNameLocked && (
                    <p className="pt-1 text-11 text-tertiary">
                      {t("workspace_settings.settings.groups.managed_externally_hint")}
                    </p>
                  )}
                </div>
                <div>
                  <label htmlFor="department-code" className="text-13 text-secondary">
                    {t("workspace_settings.settings.departments.code")}
                  </label>
                  <InputGroup size="2xl">
                    <Input
                      size="2xl"
                      id="department-code"
                      value={code}
                      onChange={(event) => setCode(event.target.value.toUpperCase())}
                      maxLength={DEPARTMENT_CODE_MAX_LENGTH}
                      autoComplete="off"
                      aria-describedby="department-code-hint"
                    />
                  </InputGroup>
                  <p id="department-code-hint" className="pt-1 text-11 text-tertiary">
                    {t("workspace_settings.settings.departments.code_hint")}
                  </p>
                </div>
                <fieldset>
                  <legend className="text-13 text-secondary">
                    {t("workspace_settings.settings.departments.color")}
                  </legend>
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <button
                      type="button"
                      aria-pressed={color === ""}
                      onClick={() => setColor("")}
                      className={`h-7 rounded-md border px-2 text-12 text-secondary ${
                        color === "" ? "border-accent-strong" : "border-subtle"
                      }`}
                    >
                      {t("workspace_settings.settings.departments.no_color")}
                    </button>
                    {DEPARTMENT_COLORS.map((option) => (
                      <button
                        key={option}
                        type="button"
                        aria-label={option}
                        aria-pressed={color.toLowerCase() === option}
                        onClick={() => setColor(option)}
                        className={`size-7 rounded-full border-2 ${
                          color.toLowerCase() === option ? "border-strong" : "border-transparent"
                        }`}
                        style={{ backgroundColor: option }}
                      />
                    ))}
                    <div className="w-28">
                      <InputGroup size="md">
                        <Input
                          size="md"
                          aria-label={t("workspace_settings.settings.departments.color")}
                          value={color}
                          onChange={(event) => setColor(event.target.value)}
                          placeholder="#3f76ff"
                          maxLength={9}
                          autoComplete="off"
                          aria-invalid={!isDepartmentColor(color.trim())}
                        />
                      </InputGroup>
                    </div>
                  </div>
                </fieldset>
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
                label={isEditing ? t("save") : t("workspace_settings.settings.departments.add")}
              />
            </DialogActions>
          </DialogMain>
        </form>
      </DialogContent>
    </Dialog>
  );
}
