/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
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
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import type { TUserGroup } from "@plane/types";
// helpers
import type { TDepartmentImportRow } from "@/helpers/department";
import { parseDepartmentList, planDepartmentImport } from "@/helpers/department";

type Props = {
  /** Every group of the workspace: what is already there decides which rows are left out. */
  groups: TUserGroup[];
  onClose: () => void;
  /** Creates the departments; resolves when all of them are there. */
  onImport: (rows: TDepartmentImportRow[]) => Promise<void>;
};

export function DepartmentImportModal(props: Props) {
  const { groups, onClose, onImport } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [text, setText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  // derived values
  const parsed = useMemo(() => parseDepartmentList(text), [text]);
  const plan = useMemo(() => planDepartmentImport(parsed.rows, groups), [parsed, groups]);
  const hasInput = text.trim().length > 0;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (plan.create.length === 0) return;
    setIsSubmitting(true);
    try {
      await onImport(plan.create);
      onClose();
    } catch {
      // the caller shows what went wrong; what was created is left out of the next try
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
                <DialogTitle>{t("workspace_settings.settings.departments.import_title")}</DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-3">
                <label htmlFor="department-import-list" className="text-13 text-secondary">
                  {t("workspace_settings.settings.departments.import_hint")}
                </label>
                <TextAreaGroup resize="vertical">
                  <TextArea
                    size="lg"
                    surface="field"
                    id="department-import-list"
                    rows={8}
                    value={text}
                    onChange={(event) => setText(event.target.value)}
                    placeholder={"RM;Marketing\nQA;Quality"}
                    spellCheck={false}
                  />
                </TextAreaGroup>
                {hasInput && (
                  <div className="flex flex-col gap-1 text-13 text-secondary" aria-live="polite">
                    <p>
                      {t("workspace_settings.settings.departments.import_summary", {
                        create: plan.create.length,
                        existing: plan.existing.length,
                      })}
                    </p>
                    {parsed.skipped.length > 0 && (
                      <p className="text-danger-primary">
                        {t("workspace_settings.settings.departments.import_invalid_lines", {
                          lines: parsed.skipped.map((skipped) => skipped.line).join(", "),
                        })}
                      </p>
                    )}
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
                disabled={plan.create.length === 0}
                label={t("workspace_settings.settings.departments.import")}
              />
            </DialogActions>
          </DialogMain>
        </form>
      </DialogContent>
    </Dialog>
  );
}
