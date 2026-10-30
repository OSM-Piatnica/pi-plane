/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { Upload } from "lucide-react";
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
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TProjectMemberImportRow, TProjectMemberImportSummary } from "@plane/types";
// helpers
import { downloadBlob, MAX_PROJECT_CSV_SIZE_BYTES } from "@/helpers/project-csv-helpers";
import {
  MEMBER_IMPORT_SAMPLE_CSV,
  chunkRows,
  mergeMemberImportSummaries,
  parseMemberImportCsv,
  skippedRowsToCsv,
} from "@/helpers/project-member-import";
// services
import { projectMemberImportService } from "@/services/project/project-member-import.service";

type Props = {
  isOpen: boolean;
  workspaceSlug: string;
  projectId: string;
  onClose: () => void;
  /** Called once an import changed who is in the project. */
  onImported: () => void | Promise<void>;
};

const plural = (count: number) => (count === 1 ? "" : "s");

/** Add people and groups to a project from a CSV file. */
export function ProjectMemberImportModal(props: Props) {
  const { isOpen, workspaceSlug, projectId, onClose, onImported } = props;
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [summary, setSummary] = useState<TProjectMemberImportSummary | null>(null);

  const close = () => {
    setSummary(null);
    setIsDragging(false);
    onClose();
  };

  const showError = (message: string) =>
    setToast({ type: "error", title: t("project.members_import.toast.invalid_file.title"), message });

  const importFile = async (file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      showError(t("project.members_import.toast.invalid_file.message"));
      return;
    }
    if (file.size > MAX_PROJECT_CSV_SIZE_BYTES) {
      showError(t("project.members_import.toast.invalid_file.message"));
      return;
    }
    const parsed = parseMemberImportCsv(await file.text());
    if (!parsed.ok) {
      showError(t(`project.members_import.parse_errors.${parsed.error}`));
      return;
    }
    setIsImporting(true);
    try {
      const answers: TProjectMemberImportSummary[] = [];
      // one chunk after the other, so rows of a later chunk see what an earlier one changed
      await chunkRows<TProjectMemberImportRow>(parsed.rows).reduce<Promise<void>>(async (previous, rows) => {
        await previous;
        answers.push(await projectMemberImportService.importRows(workspaceSlug, projectId, rows));
      }, Promise.resolve());
      setSummary(mergeMemberImportSummaries(answers));
      await onImported();
    } catch (error) {
      setToast({
        type: "error",
        title: t("project.members_import.toast.import_failed.title"),
        message: (error as { error?: string })?.error ?? t("project.members_import.toast.import_failed.message"),
      });
    } finally {
      setIsImporting(false);
    }
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    void importFile(event.target.files?.[0]);
    event.target.value = "";
  };
  const onDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setIsDragging(false);
    void importFile(event.dataTransfer.files[0]);
  };

  const downloadSample = () =>
    downloadBlob(
      new Blob([MEMBER_IMPORT_SAMPLE_CSV], { type: "text/csv;charset=utf-8" }),
      "project-members-sample.csv"
    );
  const downloadSkipped = () =>
    summary &&
    downloadBlob(new Blob([skippedRowsToCsv(summary.skipped)], { type: "text/csv;charset=utf-8" }), "skipped-rows.csv");

  const reasonOf = (item: TProjectMemberImportSummary["skipped"][number]) => {
    const key = `project.members_import.skip_reasons.${item.code}`;
    const text = t(key);
    // a code the web does not know yet shows the API's English reason
    return text === key ? item.reason : text;
  };

  const stats = summary
    ? [
        { label: t("project.members_import.summary.stats.added"), value: summary.people.added },
        { label: t("project.members_import.summary.stats.reactivated"), value: summary.people.reactivated },
        { label: t("project.members_import.summary.stats.already_members"), value: summary.people.already_members },
        { label: t("project.members_import.summary.stats.skipped"), value: summary.people.skipped },
        { label: t("project.members_import.summary.stats.groups_added"), value: summary.groups.added },
        { label: t("project.members_import.summary.stats.groups_updated"), value: summary.groups.updated },
        { label: t("project.members_import.summary.stats.groups_skipped"), value: summary.groups.skipped },
      ]
    : [];
  const imported = summary ? summary.people.added + summary.people.reactivated : 0;
  const linked = summary ? summary.groups.added + summary.groups.updated : 0;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogContent size="lg">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>
                {summary ? t("project.members_import.summary.title.complete") : t("project.members_import.title")}
              </DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            {summary ? (
              <div className="flex flex-col gap-4">
                <p className="text-13 text-secondary">
                  {imported + linked === 0 ? (
                    t("project.members_import.summary.message.no_imports")
                  ) : (
                    <>
                      {imported > 0 &&
                        t("project.members_import.summary.message.success", {
                          count: imported,
                          plural: plural(imported),
                        })}
                      {imported > 0 && linked > 0 && " "}
                      {linked > 0 &&
                        t("project.members_import.summary.message.groups_success", {
                          count: linked,
                          plural: plural(linked),
                        })}
                    </>
                  )}
                </p>
                <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {stats.map((stat) => (
                    <div key={stat.label} className="rounded-md border border-subtle p-2">
                      <dt className="text-11 text-tertiary">{stat.label}</dt>
                      <dd className="text-16 font-medium text-primary">{stat.value}</dd>
                    </div>
                  ))}
                </dl>
                {summary.skipped.length > 0 && (
                  <>
                    <ul className="flex max-h-48 flex-col gap-1 overflow-y-auto text-13 text-secondary">
                      {summary.skipped.map((item) => (
                        <li key={`${item.row}-${item.code}`}>
                          <span className="text-tertiary">#{item.row}</span>{" "}
                          <span className="font-medium text-primary">{item.value}</span> {reasonOf(item)}
                        </li>
                      ))}
                    </ul>
                    <div>
                      <Button
                        variant="secondary"
                        size="md"
                        stretch="auto"
                        onClick={downloadSkipped}
                        label={t("project.members_import.summary.download_errors")}
                      />
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <p className="text-13 leading-6 text-secondary">{t("project.members_import.description")}</p>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={onFileChange}
                  aria-label={t("project.members_import.dropzone.inactive")}
                />
                <button
                  type="button"
                  disabled={isImporting}
                  onClick={() => inputRef.current?.click()}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={onDrop}
                  className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-subtle p-8 text-13 text-secondary"
                >
                  <Upload className="h-5 w-5" aria-hidden="true" />
                  <span>
                    {isImporting
                      ? t("project.members_import.progress.importing")
                      : isDragging
                        ? t("project.members_import.dropzone.active")
                        : t("project.members_import.dropzone.inactive")}
                  </span>
                  <span className="text-11 text-tertiary">{t("project.members_import.dropzone.file_type")}</span>
                </button>
                <div>
                  <Button
                    variant="secondary"
                    size="md"
                    stretch="auto"
                    onClick={downloadSample}
                    label={t("project.members_import.download_sample")}
                  />
                </div>
              </div>
            )}
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button
            variant={summary ? "primary" : "secondary"}
            size="md"
            stretch="auto"
            onClick={close}
            label={summary ? t("project.members_import.buttons.done") : t("project.members_import.buttons.cancel")}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
}
