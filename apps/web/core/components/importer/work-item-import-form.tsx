import { useRef, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { Upload } from "lucide-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { ProjectDropdown } from "@/components/dropdowns/project/dropdown";
import { getApiErrorMessage } from "@/helpers/api-error";
import { getProjectImportLink, MAX_PROJECT_CSV_SIZE_BYTES } from "@/helpers/project-csv-helpers";
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { ProjectImportService } from "@/services/project/project-import.service";
import { SettingsBoxedControlItem } from "../settings/boxed-control-item";

const projectImportService = new ProjectImportService();

type Props = {
  mutateServices: () => void;
};

type FormData = {
  projectId: string;
};

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx", ".json"];

function isValidWorkItemImportFile(file: File): boolean {
  const lower = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export const WorkItemImportForm = observer(function WorkItemImportForm(props: Props) {
  const { mutateServices } = props;
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const { joinedProjectIds } = useProject();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { control, handleSubmit, watch, reset } = useForm<FormData>({
    defaultValues: { projectId: "" },
  });

  const projectId = watch("projectId");
  const canImport = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );
  const hasProjects = joinedProjectIds.length > 0;

  const onSubmit = async (formData: FormData) => {
    if (!workspaceSlug || !selectedFile || !formData.projectId) return;

    if (!isValidWorkItemImportFile(selectedFile)) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("workspace_settings.settings.imports.work_items.invalid_file_type"),
      });
      return;
    }

    if (selectedFile.size > MAX_PROJECT_CSV_SIZE_BYTES) {
      const maxMb = Math.round(MAX_PROJECT_CSV_SIZE_BYTES / (1024 * 1024));
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("workspace_settings.settings.imports.file_too_large", { size: maxMb }),
      });
      return;
    }

    setImportLoading(true);
    try {
      const result = await projectImportService.importWorkItems(
        workspaceSlug.toString(),
        formData.projectId,
        selectedFile
      );
      mutateServices();
      setSelectedFile(null);
      reset({ projectId: formData.projectId });
      if (fileInputRef.current) fileInputRef.current.value = "";

      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("workspace_settings.settings.imports.work_items.toasts.success.message", {
          count: result.created_work_items,
          name: result.project_name,
        }),
      });

      window.location.href = getProjectImportLink(workspaceSlug.toString(), result.project_id);
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: getApiErrorMessage(
          error as unknown,
          t("workspace_settings.settings.imports.work_items.toasts.error.message")
        ),
      });
    } finally {
      setImportLoading(false);
    }
  };

  return (
    <form
      onSubmit={(e) => {
        void handleSubmit(onSubmit)(e);
      }}
      className="flex flex-col gap-5"
    >
      <SettingsBoxedControlItem
        title={t("workspace_settings.settings.imports.work_items.heading")}
        description={t("workspace_settings.settings.imports.work_items.description")}
      />
      <div className="rounded-lg border border-subtle bg-layer-2">
        <SettingsBoxedControlItem
          className="rounded-none border-0 border-b"
          title={t("workspace_settings.settings.imports.work_items.select_project")}
          control={
            <Controller
              control={control}
              name="projectId"
              render={({ field: { value, onChange } }) => (
                <div className="h-7 w-full max-w-72">
                  <ProjectDropdown
                    value={value || null}
                    onChange={(val: string) => onChange(val)}
                    multiple={false}
                    buttonVariant="border-with-text"
                    placeholder={
                      hasProjects
                        ? t("workspace_settings.settings.imports.work_items.select_project_placeholder")
                        : t("workspace_settings.settings.imports.work_items.no_projects")
                    }
                    disabled={!canImport || !hasProjects || importLoading}
                  />
                </div>
              )}
            />
          }
        />
        <SettingsBoxedControlItem
          className="rounded-none border-0"
          title={t("workspace_settings.settings.imports.work_items.select_file_label")}
          control={
            <div className="flex w-full flex-col gap-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.json,text/csv,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                className="hidden"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={!canImport || importLoading}
                  prependIcon={<Upload className="size-4" />}
                >
                  {t("workspace_settings.settings.imports.work_items.select_file")}
                </Button>
                {selectedFile && <span className="max-w-md truncate text-13 text-secondary">{selectedFile.name}</span>}
              </div>
              <Button
                variant="primary"
                type="submit"
                disabled={!canImport || !selectedFile || !projectId || importLoading}
                loading={importLoading}
              >
                {t("workspace_settings.settings.imports.work_items.import_button")}
              </Button>
            </div>
          }
        />
      </div>
    </form>
  );
});
