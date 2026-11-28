/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Badge } from "@makeplane/propel/components/badge";
import { Banner } from "@makeplane/propel/components/banner";
import { Button } from "@makeplane/propel/components/button";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import type { TDocumentLibrary, TDocumentLibraryCreate, TDocumentLibraryUpdate } from "@plane/types";
// helpers
import { getDocumentLibrariesKey, getDocumentLibraryErrorMessage } from "@/helpers/document-library";
// services
import { documentLibraryService } from "@/services/document-library.service";
// local imports
import { AddDocumentLibraryModal } from "./add-library-modal";
import { EditDocumentLibraryModal } from "./edit-library-modal";

type Props = {
  workspaceSlug: string;
};

const T = "workspace_settings.settings.document_libraries";

export const DocumentLibrariesSettings = observer(function DocumentLibrariesSettings(props: Props) {
  const { workspaceSlug } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editing, setEditing] = useState<TDocumentLibrary | null>(null);
  const [toRemove, setToRemove] = useState<TDocumentLibrary | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const [isBusy, setIsBusy] = useState(false);

  const { data, mutate } = useSWR(getDocumentLibrariesKey(workspaceSlug), () =>
    documentLibraryService.list(workspaceSlug)
  );

  const showError = (error: unknown) =>
    setToast({
      type: "error",
      title: t("toast.error"),
      message: getDocumentLibraryErrorMessage(error, t, t("something_went_wrong_please_try_again")),
    });
  const showSuccess = (message: string) => setToast({ type: "success", title: t("toast.success"), message });

  const handleAdd = async (body: TDocumentLibraryCreate) => {
    try {
      await documentLibraryService.create(workspaceSlug, body);
      await mutate();
      showSuccess(t(`${T}.added`));
    } catch (error) {
      showError(error);
      throw error;
    }
  };

  const handleEdit = async (library: TDocumentLibrary, body: TDocumentLibraryUpdate) => {
    try {
      await documentLibraryService.update(workspaceSlug, library.id, body);
      await mutate();
      showSuccess(t(`${T}.updated`));
    } catch (error) {
      showError(error);
      throw error;
    }
  };

  const handleSetDefault = async (libraryId: string | null) => {
    setIsBusy(true);
    try {
      await documentLibraryService.setDefault(workspaceSlug, libraryId);
      await mutate();
    } catch (error) {
      showError(error);
    } finally {
      setIsBusy(false);
    }
  };

  const handleRemove = async () => {
    if (!toRemove) return;
    setIsRemoving(true);
    try {
      await documentLibraryService.remove(workspaceSlug, toRemove.id);
      await mutate();
      setToRemove(null);
      showSuccess(t(`${T}.removed`));
    } catch (error) {
      showError(error);
    } finally {
      setIsRemoving(false);
    }
  };

  const sharepointEnabled = data?.sharepoint_enabled ?? false;
  const libraries = data?.libraries ?? [];

  return (
    <section className="size-full">
      <div className="flex items-start justify-between gap-4 pb-4">
        <div className="flex flex-col gap-1">
          <h4 className="text-h3-medium">{t(`${T}.title`)}</h4>
          <p className="text-13 text-secondary">{t(`${T}.description`)}</p>
        </div>
        <Button
          size="md"
          stretch="auto"
          variant="primary"
          disabled={!sharepointEnabled}
          onClick={() => setIsAddOpen(true)}
          label={t(`${T}.add`)}
        />
      </div>

      {data && !sharepointEnabled && (
        <div className="pb-4">
          <Banner
            placement="inline"
            variant="warning"
            title={t(`${T}.not_configured_title`)}
            description={t(`${T}.errors.not_configured`)}
          />
        </div>
      )}

      {data && (
        <ul className="flex flex-col divide-y divide-subtle rounded-lg border border-subtle">
          <li className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-14 font-medium text-primary">{t(`${T}.native.name`)}</span>
                {data.native.is_default && <Badge variant="neutral" size="sm" label={t(`${T}.default`)} />}
              </div>
              <p className="text-11 text-tertiary">{t(`${T}.native.description`)}</p>
            </div>
            {!data.native.is_default && (
              <Button
                size="md"
                stretch="auto"
                variant="secondary"
                disabled={isBusy}
                onClick={() => void handleSetDefault(null)}
                label={t(`${T}.make_default`)}
              />
            )}
          </li>
          {libraries.map((library) => (
            <li key={library.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-14 font-medium text-primary">{library.name}</span>
                  <span className="rounded-sm bg-layer-1 px-1.5 py-0.5 text-11 text-secondary">SharePoint</span>
                  {library.is_default && <Badge variant="neutral" size="sm" label={t(`${T}.default`)} />}
                </div>
                <p className="text-11 text-tertiary">
                  {t(`${T}.root_folder_value`, { folder: library.root_path || "/" })}
                  {" · "}
                  {t(`${T}.usage`, {
                    documents: library.document_count ?? 0,
                    projects: library.project_count ?? 0,
                  })}
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                {library.folder_web_url && (
                  <a
                    href={library.folder_web_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-13 text-accent-primary hover:underline"
                  >
                    {t(`${T}.open_in_sharepoint`)}
                  </a>
                )}
                {!library.is_default && (
                  <Button
                    size="md"
                    stretch="auto"
                    variant="secondary"
                    disabled={isBusy}
                    onClick={() => void handleSetDefault(library.id)}
                    label={t(`${T}.make_default`)}
                  />
                )}
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  onClick={() => setEditing(library)}
                  label={t(`${T}.edit`)}
                />
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  onClick={() => setToRemove(library)}
                  label={t(`${T}.remove`)}
                />
              </div>
            </li>
          ))}
        </ul>
      )}

      {data && libraries.length > 0 && !data.native.is_default && !sharepointEnabled && (
        <p className="pt-2 text-11 text-tertiary">{t(`${T}.default_inactive`)}</p>
      )}

      {isAddOpen && (
        <AddDocumentLibraryModal
          workspaceSlug={workspaceSlug}
          onClose={() => setIsAddOpen(false)}
          onSubmit={handleAdd}
        />
      )}
      {editing && (
        <EditDocumentLibraryModal
          key={editing.id}
          library={editing}
          onClose={() => setEditing(null)}
          onSubmit={(body) => handleEdit(editing, body)}
        />
      )}
      <ConfirmDialog
        isOpen={toRemove !== null}
        handleClose={() => setToRemove(null)}
        handleSubmit={handleRemove}
        isSubmitting={isRemoving}
        title={t(`${T}.remove_title`, { name: toRemove?.name ?? "" })}
        content={t(`${T}.remove_content`)}
        primaryButtonText={{ loading: t(`${T}.removing`), default: t(`${T}.remove`) }}
        secondaryButtonText={t("cancel")}
      />
    </section>
  );
});
