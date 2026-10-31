/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { CheckboxField } from "@makeplane/propel/components/checkbox-field";
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
import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { setToast } from "@plane/blocks/toast";
import { EXPORTERS_LIST } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
// helpers
import { getApiErrorMessage } from "@/helpers/api-error";
import { downloadBlob } from "@/helpers/project-csv-helpers";
import { buildMemberExportParams } from "@/helpers/project-member-export";
// services
import { projectMemberExportService } from "@/services/project/project-member-export.service";

type Props = {
  isOpen: boolean;
  workspaceSlug: string;
  projectId: string;
  onClose: () => void;
};

/** Download the members of a project as CSV, Excel or JSON; the file can be imported again as CSV. */
export function ProjectMemberExportModal(props: Props) {
  const { isOpen, workspaceSlug, projectId, onClose } = props;
  const { t } = useTranslation();
  const [choiceIndex, setChoiceIndex] = useState(0);
  const [includeViaGroup, setIncludeViaGroup] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const options = EXPORTERS_LIST.map((exporter, index) => ({ label: t(exporter.i18n_title), value: String(index) }));

  const exportMembers = async () => {
    setIsExporting(true);
    try {
      const choice = EXPORTERS_LIST[choiceIndex];
      const { blob, filename } = await projectMemberExportService.download(
        workspaceSlug,
        projectId,
        buildMemberExportParams(choice, includeViaGroup)
      );
      downloadBlob(blob, filename);
      onClose();
    } catch (error) {
      setToast({
        type: "error",
        title: t("project.members_export.toast.failed.title"),
        message: getApiErrorMessage(error as { error?: string }, t("project.members_export.toast.failed.message")),
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !isExporting && onClose()}>
      <DialogContent size="lg">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>{t("project.members_export.title")}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            <div className="flex flex-col gap-4">
              <p className="text-13 leading-6 text-secondary">{t("project.members_export.description")}</p>
              <div className="flex flex-col gap-1">
                <span className="text-13 font-medium text-primary">{t("project.members_export.format")}</span>
                <Select<string>
                  items={options}
                  value={String(choiceIndex)}
                  onValueChange={(value) => setChoiceIndex(Number(value))}
                  disabled={isExporting}
                >
                  <SelectTrigger size="md" placeholder={t("project.members_export.format")} />
                  <SelectContent side="bottom" align="start">
                    <SelectList>
                      {options.map((option) => (
                        <SelectItem key={option.value} value={option.value} size="md" label={option.label} />
                      ))}
                    </SelectList>
                  </SelectContent>
                </Select>
              </div>
              <CheckboxField
                name="include_via_group"
                label={t("project.members_export.include_via_group.label")}
                description={t("project.members_export.include_via_group.description")}
                size="lg"
                stretch="full"
                checked={includeViaGroup}
                onCheckedChange={(checked) => setIncludeViaGroup(checked === true)}
                disabled={isExporting}
              />
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            onClick={onClose}
            disabled={isExporting}
            label={t("project.members_export.buttons.cancel")}
          />
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            onClick={() => void exportMembers()}
            loading={isExporting}
            label={
              isExporting ? t("project.members_export.buttons.exporting") : t("project.members_export.buttons.export")
            }
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
}
