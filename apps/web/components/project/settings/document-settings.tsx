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
import { Banner } from "@makeplane/propel/components/banner";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { setToast } from "@plane/blocks/toast";
import type { TProjectDocumentSettings, TProjectDocumentStore } from "@plane/types";
// helpers
import {
  getDocumentLibraryErrorMessage,
  getProjectDocumentSettingsKey,
  getProjectDocumentFormState,
  getProjectFolderPreview,
} from "@/helpers/document-library";
// services
import { documentLibraryService } from "@/services/document-library.service";

type Props = {
  workspaceSlug: string;
  projectId: string;
};

const T = "project_settings.documents";

/** Where new documents of a project go, and a link to its folder in SharePoint (docs/document-libraries.md). */
export const ProjectDocumentSettings = observer(function ProjectDocumentSettings(props: Props) {
  const { workspaceSlug, projectId } = props;
  const { data, mutate } = useSWR(getProjectDocumentSettingsKey(workspaceSlug, projectId), () =>
    documentLibraryService.getProjectSettings(workspaceSlug, projectId)
  );
  if (!data) return null;
  // A fresh form for every saved state, so the fields start from what the server says
  return (
    <ProjectDocumentSettingsForm
      key={`${data.store}-${data.library_id ?? ""}-${data.folder}`}
      workspaceSlug={workspaceSlug}
      projectId={projectId}
      settings={data}
      onSaved={(saved) => mutate(saved, { revalidate: false })}
    />
  );
});

type FormProps = Props & {
  settings: TProjectDocumentSettings;
  onSaved: (settings: TProjectDocumentSettings) => void;
};

function ProjectDocumentSettingsForm(props: FormProps) {
  const { workspaceSlug, projectId, settings, onSaved } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [store, setStore] = useState<TProjectDocumentStore>(settings.store);
  const [libraryId, setLibraryId] = useState(settings.library_id ?? settings.libraries[0]?.id ?? "");
  const [folder, setFolder] = useState(settings.folder);
  const [isSaving, setIsSaving] = useState(false);

  // derived values
  const form = getProjectDocumentFormState(settings, { store, libraryId, folder });
  const storeOptions: { value: TProjectDocumentStore; label: string; disabled?: boolean }[] = [
    {
      value: "workspace",
      label: t(`${T}.store.workspace`, { name: settings.workspace_default?.name ?? t(`${T}.native_name`) }),
    },
    { value: "sharepoint", label: t(`${T}.store.sharepoint`), disabled: settings.libraries.length === 0 },
    { value: "native", label: t(`${T}.store.native`) },
  ];

  const handleSave = async () => {
    if (!form.canSave || isSaving || form.folder === null) return;
    setIsSaving(true);
    try {
      const saved = await documentLibraryService.updateProjectSettings(workspaceSlug, projectId, {
        store,
        library_id: store === "sharepoint" ? libraryId : null,
        folder: store === "native" ? "" : form.folder,
      });
      onSaved(saved);
      setToast({ type: "success", title: t("toast.success"), message: t(`${T}.saved`) });
    } catch (error) {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: getDocumentLibraryErrorMessage(error, t, t("something_went_wrong_please_try_again")),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {!settings.sharepoint_enabled && (
        <Banner
          placement="inline"
          variant="warning"
          title={t("workspace_settings.settings.document_libraries.not_configured_title")}
          description={t(`${T}.not_configured`)}
        />
      )}

      <ProjectDocumentLocation workspaceSlug={workspaceSlug} projectId={projectId} settings={settings} />

      <fieldset className="flex flex-col gap-2" disabled={!settings.can_edit}>
        <legend className="pb-1 text-13 font-medium text-primary">{t(`${T}.store.label`)}</legend>
        {storeOptions.map((option) => (
          <label key={option.value} className="flex items-center gap-2 text-13 text-primary">
            <input
              type="radio"
              name="project-document-store"
              value={option.value}
              checked={store === option.value}
              disabled={option.disabled}
              onChange={() => setStore(option.value)}
            />
            {option.label}
          </label>
        ))}
        {settings.libraries.length === 0 && <p className="text-11 text-tertiary">{t(`${T}.no_libraries`)}</p>}
      </fieldset>

      {store === "sharepoint" && settings.libraries.length > 0 && (
        <LibrarySelect settings={settings} value={libraryId} onChange={setLibraryId} />
      )}

      {store !== "native" && (
        <ProjectFolderField
          settings={settings}
          value={folder}
          onChange={setFolder}
          preview={getProjectFolderPreview(form.rootPath, form.folder ?? "", settings.default_folder)}
          isValid={form.folder !== null}
        />
      )}

      {settings.can_edit && (
        <div className="flex flex-col items-start gap-2">
          <p className="text-11 text-tertiary">{t(`${T}.existing_stay`)}</p>
          <Button
            size="md"
            stretch="auto"
            variant="primary"
            loading={isSaving}
            disabled={!form.canSave || isSaving}
            onClick={() => void handleSave()}
            label={t("save")}
          />
        </div>
      )}
    </div>
  );
}

function LibrarySelect(props: {
  settings: TProjectDocumentSettings;
  value: string;
  onChange: (libraryId: string) => void;
}) {
  const { settings, value, onChange } = props;
  const { t } = useTranslation();
  const options = settings.libraries.map((library) => ({ label: library.name, value: library.id }));
  return (
    <div className="flex max-w-md flex-col gap-1">
      <span className="text-13 text-secondary">{t(`${T}.library`)}</span>
      <Select<string>
        items={options}
        value={value}
        onValueChange={(next) => onChange(next ?? "")}
        disabled={!settings.can_edit}
      >
        <SelectTrigger size="md" placeholder={t(`${T}.library`)} />
        <SelectContent side="bottom" align="start">
          <SelectList>
            {options.map((option) => (
              <SelectItem key={option.value} value={option.value} size="md" label={option.label} />
            ))}
          </SelectList>
        </SelectContent>
      </Select>
    </div>
  );
}

function ProjectFolderField(props: {
  settings: TProjectDocumentSettings;
  value: string;
  onChange: (folder: string) => void;
  preview: string;
  isValid: boolean;
}) {
  const { settings, value, onChange, preview, isValid } = props;
  const { t } = useTranslation();
  return (
    <div className="flex max-w-md flex-col gap-1">
      <label htmlFor="project-document-folder" className="text-13 text-secondary">
        {t(`${T}.folder`)}
      </label>
      <InputGroup size="2xl">
        <Input
          size="2xl"
          id="project-document-folder"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={settings.default_folder}
          disabled={!settings.can_edit}
          autoComplete="off"
        />
      </InputGroup>
      <p className="text-11 text-tertiary">
        {t(`${T}.folder_hint`, { path: preview, identifier: settings.default_folder })}
      </p>
      {!isValid && (
        <p role="alert" className="text-11 text-danger-primary">
          {t("workspace_settings.settings.document_libraries.errors.invalid_folder")}
        </p>
      )}
    </div>
  );
}

/** Where new documents go now, with the link to the project's folder in SharePoint. */
function ProjectDocumentLocation(props: Props & { settings: TProjectDocumentSettings }) {
  const { workspaceSlug, projectId, settings } = props;
  const { t } = useTranslation();
  const { effective } = settings;
  const isSharePoint = effective.provider === "sharepoint";
  // Asks SharePoint whether the folder is there yet; it is made by the first upload
  const { data: folder, error } = useSWR(
    isSharePoint ? `PROJECT_DOCUMENT_FOLDER_${projectId}_${effective.library?.id}_${effective.folder}` : null,
    () => documentLibraryService.getProjectFolder(workspaceSlug, projectId),
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );

  return (
    <div className="flex flex-col gap-1 rounded-lg border border-subtle px-4 py-3">
      <span className="text-13 font-medium text-primary">{t(`${T}.current.label`)}</span>
      {isSharePoint ? (
        <>
          <span className="text-13 text-secondary">
            {t(`${T}.current.sharepoint`, { library: effective.library?.name ?? "", folder: effective.folder })}
          </span>
          {folder && (
            <span className="flex flex-wrap items-center gap-2 text-13">
              <a
                href={folder.web_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-primary hover:underline"
              >
                {folder.exists ? t(`${T}.open_folder`) : t(`${T}.open_root_folder`)}
              </a>
              {!folder.exists && <span className="text-11 text-tertiary">{t(`${T}.folder_not_yet`)}</span>}
            </span>
          )}
          {error && (
            <span className="flex flex-wrap items-center gap-2 text-13">
              {effective.folder_web_url && (
                <a
                  href={effective.folder_web_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent-primary hover:underline"
                >
                  {t(`${T}.open_folder`)}
                </a>
              )}
              <span role="alert" className="text-11 text-danger-primary">
                {getDocumentLibraryErrorMessage(error, t, t("something_went_wrong_please_try_again"))}
              </span>
            </span>
          )}
        </>
      ) : (
        <span className="text-13 text-secondary">
          {t(`${T}.current.native.${effective.native_reason || "no_library"}`)}
        </span>
      )}
    </div>
  );
}
