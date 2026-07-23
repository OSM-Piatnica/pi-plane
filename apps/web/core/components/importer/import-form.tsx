import { useRef, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Upload } from "lucide-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import {
  getProjectImportLink,
  isValidProjectCsvFile,
  isValidProjectCsvSize,
  MAX_PROJECT_CSV_SIZE_BYTES,
} from "@/helpers/project-csv-helpers";
import { getApiErrorMessage } from "@/helpers/api-error";
import { useUserPermissions } from "@/hooks/store/user";
import { ProjectImportService } from "@/services/project/project-import.service";
import { SettingsBoxedControlItem } from "../settings/boxed-control-item";

const projectImportService = new ProjectImportService();

type Props = {
  mutateServices: () => void;
};

export const ImportForm = observer(function ImportForm(props: Props) {
  const { mutateServices } = props;
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const canImport = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
  };

  const handleImport = async () => {
    if (!workspaceSlug || !selectedFile) return;

    if (!isValidProjectCsvFile(selectedFile)) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("workspace_settings.settings.imports.invalid_file_type"),
      });
      return;
    }

    if (!isValidProjectCsvSize(selectedFile)) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("workspace_settings.settings.imports.file_too_large", {
          size: Math.round(MAX_PROJECT_CSV_SIZE_BYTES / (1024 * 1024)),
        }),
      });
      return;
    }

    setImportLoading(true);
    try {
      const result = await projectImportService.importProjectCsv(workspaceSlug.toString(), selectedFile);
      const firstProject = result.projects[0];
      mutateServices();
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";

      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: firstProject
          ? t("workspace_settings.settings.imports.toasts.success.message", {
              name: firstProject.project_name,
            })
          : result.message,
      });

      if (firstProject && result.projects.length === 1) {
        window.location.href = getProjectImportLink(workspaceSlug.toString(), firstProject.project_id);
      }
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: getApiErrorMessage(error as unknown, t("workspace_settings.settings.imports.toasts.error.message")),
      });
    } finally {
      setImportLoading(false);
    }
  };

  return (
    <SettingsBoxedControlItem
      className="md:flex-col md:items-stretch"
      title={t("workspace_settings.settings.imports.heading")}
      description={t("workspace_settings.settings.imports.description")}
      control={
        <div className="flex w-full flex-col gap-4">
          <input ref={fileInputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={handleFileChange} />
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={!canImport || importLoading}
              prependIcon={<Upload className="size-4" />}
            >
              {t("workspace_settings.settings.imports.select_file")}
            </Button>
            {selectedFile && <span className="max-w-md truncate text-13 text-secondary">{selectedFile.name}</span>}
          </div>
          <Button
            variant="primary"
            onClick={handleImport}
            disabled={!canImport || !selectedFile || importLoading}
            loading={importLoading}
          >
            {t("workspace_settings.settings.imports.import_button")}
          </Button>
        </div>
      }
    />
  );
});
