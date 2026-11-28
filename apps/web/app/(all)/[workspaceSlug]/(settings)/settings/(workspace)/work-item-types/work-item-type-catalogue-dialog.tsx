/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import useSWR from "swr";
import { Logo } from "@plane/blocks/emoji-icon-picker";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Checkbox } from "@makeplane/propel/components/checkbox";
import { Dialog, DialogBody, DialogContent, DialogMain } from "@makeplane/propel/components/dialog";
import type { TIssueTypeCatalogueEntry } from "@plane/types";
import { LogoSpinner } from "@/components/common/logo-spinner";
import { IssueTypeService } from "@/services/issue-type.service";
import { getNewCatalogueKeys, toggleCatalogueKey } from "./work-item-type-catalogue-helpers";

const service = new IssueTypeService();

type Props = {
  workspaceSlug: string;
  isOpen: boolean;
  onClose: () => void;
  /** Called after types were added, to reload the list */
  onAdded: () => Promise<unknown>;
};

/** "Add from catalogue": ready-made types with an icon, a description template and suggested properties. */
export function WorkItemTypeCatalogueDialog(props: Props) {
  const { workspaceSlug, isOpen, onClose, onAdded } = props;
  const { t, currentLocale } = useTranslation();
  const { data: entries, isLoading } = useSWR(
    isOpen ? `ISSUE_TYPE_CATALOGUE_${workspaceSlug}_${currentLocale}` : null,
    () => service.listCatalogue(workspaceSlug, currentLocale)
  );
  // null: nothing picked by hand yet, so every entry the workspace does not have is selected
  const [picked, setPicked] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);
  const selected = picked ?? getNewCatalogueKeys(entries ?? []);
  const selectedSet = new Set(selected);

  const close = () => {
    setPicked(null);
    onClose();
  };

  const onSubmit = async () => {
    if (selected.length === 0) return;
    setSaving(true);
    try {
      await service.addFromCatalogue(workspaceSlug, selected, currentLocale);
      await onAdded();
      setToast({
        type: "success",
        title: t("workspace_settings.settings.work_item_types.catalogue.toasts.added.title"),
        message: t("workspace_settings.settings.work_item_types.catalogue.toasts.added.message"),
      });
      close();
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
        title: t("workspace_settings.settings.work_item_types.catalogue.toasts.add_failed.title"),
        message: t("workspace_settings.settings.work_item_types.catalogue.toasts.add_failed.message"),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <DialogContent size="lg">
        <DialogMain>
          <DialogBody tabIndex={0}>
            <div className="p-1">
              <h3 className="text-h3-medium text-primary">
                {t("workspace_settings.settings.work_item_types.catalogue.title")}
              </h3>
              <p className="pt-1 pb-4 text-13 text-tertiary">
                {t("workspace_settings.settings.work_item_types.catalogue.intro")}
              </p>
              {isLoading || !entries ? (
                <div className="flex justify-center py-8">
                  <LogoSpinner />
                </div>
              ) : (
                <ul className="space-y-2">
                  {entries.map((entry) => (
                    <CatalogueRow
                      key={entry.key}
                      entry={entry}
                      checked={selectedSet.has(entry.key)}
                      onToggle={() => setPicked(toggleCatalogueKey(selected, entry.key))}
                    />
                  ))}
                </ul>
              )}
              <div className="flex justify-end gap-2 pt-4">
                <Button size="md" stretch="auto" variant="secondary" onClick={close} label={t("cancel")} />
                <Button
                  size="md"
                  stretch="auto"
                  variant="primary"
                  onClick={onSubmit}
                  disabled={saving || selected.length === 0}
                  loading={saving}
                  label={t("workspace_settings.settings.work_item_types.catalogue.add_selected")}
                />
              </div>
            </div>
          </DialogBody>
        </DialogMain>
      </DialogContent>
    </Dialog>
  );
}

type TCatalogueRowProps = {
  entry: TIssueTypeCatalogueEntry;
  checked: boolean;
  onToggle: () => void;
};

function CatalogueRow(props: TCatalogueRowProps) {
  const { entry, checked, onToggle } = props;
  const { t } = useTranslation();
  const inWorkspace = !!entry.existing_type_id;
  const properties = entry.properties.map((prop) => prop.title).join(", ");

  return (
    <li className="flex items-start gap-3 rounded-md border border-subtle p-3">
      <Checkbox
        checked={!inWorkspace && checked}
        disabled={inWorkspace}
        onCheckedChange={onToggle}
        aria-label={entry.name}
      />
      <span className="grid size-6 shrink-0 place-items-center">
        <Logo logo={entry.logo_props} size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-13 font-medium text-primary">
          <span>{entry.name}</span>
          {entry.is_default ? (
            <span className="rounded bg-surface-2 px-1.5 py-0.5 text-10 text-tertiary">
              {t("workspace_settings.settings.work_item_types.catalogue.default_badge")}
            </span>
          ) : null}
          {entry.kind === "milestone" ? (
            <span className="rounded bg-surface-2 px-1.5 py-0.5 text-10 text-tertiary">
              {t("workspace_settings.settings.work_item_types.kinds.milestone")}
            </span>
          ) : null}
          {inWorkspace ? (
            <span className="font-normal text-11 text-tertiary">
              {t("workspace_settings.settings.work_item_types.catalogue.in_workspace")}
            </span>
          ) : null}
        </div>
        <p className="text-12 text-secondary">{entry.description}</p>
        <p className="pt-0.5 text-11 text-tertiary">
          {properties
            ? t("workspace_settings.settings.work_item_types.catalogue.properties", { properties })
            : t("workspace_settings.settings.work_item_types.catalogue.no_properties")}
        </p>
      </div>
    </li>
  );
}
