import { useState } from "react";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
import { EUserPermissions, EUserPermissionsLevel, PROJECT_EXPORT_FORMATS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomSelect, ToggleSwitch } from "@plane/ui";
import { ProjectDropdown } from "@/components/dropdowns/project/dropdown";
import { getApiErrorMessage } from "@/helpers/api-error";
import { downloadBlob } from "@/helpers/project-csv-helpers";
import { useProject } from "@/hooks/store/use-project";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { ProjectExportService } from "@/services/project/project-export.service";
import { SettingsBoxedControlItem } from "../settings/boxed-control-item";

type Props = {
  workspaceSlug: string;
};

type FormData = {
  projectId: string;
  format: (typeof PROJECT_EXPORT_FORMATS)[number];
  includeWorkItems: boolean;
};

const projectExportService = new ProjectExportService();

export const ProjectExportForm = observer(function ProjectExportForm(props: Props) {
  const { workspaceSlug } = props;
  const [exportLoading, setExportLoading] = useState(false);
  const { allowPermissions } = useUserPermissions();
  const { projectsWithCreatePermissions } = useUser();
  const { joinedProjectIds, getProjectById } = useProject();
  const { t } = useTranslation();
  const { handleSubmit, control, watch } = useForm<FormData>({
    defaultValues: {
      projectId: "",
      format: PROJECT_EXPORT_FORMATS[0],
      includeWorkItems: false,
    },
  });

  const includeWorkItems = watch("includeWorkItems");
  const hasProjects = joinedProjectIds.length > 0;
  const isMember = allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.WORKSPACE);

  const onSubmit = async (formData: FormData) => {
    if (!formData.projectId) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("workspace_settings.settings.exports.project_csv.toasts.error.message"),
      });
      return;
    }

    setExportLoading(true);
    try {
      const blob = await projectExportService.exportProject(workspaceSlug, [formData.projectId], {
        provider: formData.format.provider,
        delimiter: "delimiter" in formData.format ? formData.format.delimiter : undefined,
        includeWorkItems: formData.includeWorkItems,
      });
      const project = getProjectById(formData.projectId);
      const extension = formData.includeWorkItems ? "csv" : formData.format.extension;
      const suffix = formData.includeWorkItems ? "full" : "config";
      const filename = `${project?.identifier ?? "project"}-${suffix}.${extension}`;
      downloadBlob(blob, filename);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("workspace_settings.settings.exports.project_csv.toasts.success.title"),
        message: formData.includeWorkItems
          ? t("workspace_settings.settings.exports.project_csv.toasts.success_full.message")
          : t("workspace_settings.settings.exports.project_csv.toasts.success.message"),
      });
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("workspace_settings.settings.exports.project_csv.toasts.error.title"),
        message: getApiErrorMessage(
          error as unknown,
          t("workspace_settings.settings.exports.project_csv.toasts.error.message")
        ),
      });
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <SettingsBoxedControlItem
      className="md:flex-col md:items-stretch"
      title={t("workspace_settings.settings.exports.project_csv.heading")}
      description={t("workspace_settings.settings.exports.project_csv.description")}
      control={
        <form onSubmit={handleSubmit(onSubmit)} className="flex w-full flex-col gap-4">
          <div className="flex flex-col gap-2">
            <p className="text-13 text-secondary">
              {t("workspace_settings.settings.exports.project_csv.select_project")}
            </p>
            <Controller
              control={control}
              name="projectId"
              render={({ field: { value, onChange } }) => (
                <div className="h-7">
                  <ProjectDropdown
                    value={value || null}
                    onChange={onChange}
                    multiple={false}
                    buttonVariant="border-with-text"
                    disabled={!hasProjects || !isMember}
                    placeholder={t("workspace_settings.settings.exports.project_csv.select_project")}
                    renderCondition={
                      projectsWithCreatePermissions
                        ? (projectId) => !!projectsWithCreatePermissions[projectId]
                        : undefined
                    }
                  />
                </div>
              )}
            />
          </div>
          <div className="flex flex-col gap-2">
            <p className="text-13 text-secondary">
              {t("workspace_settings.settings.exports.project_csv.select_format")}
            </p>
            <Controller
              control={control}
              name="format"
              render={({ field: { value, onChange } }) => (
                <CustomSelect
                  value={value}
                  onChange={onChange}
                  label={t(value.i18n_title)}
                  optionsClassName="w-48"
                  placement="bottom-end"
                  buttonClassName="py-2 text-13"
                  disabled={!isMember || includeWorkItems}
                >
                  {PROJECT_EXPORT_FORMATS.map((format) => (
                    <CustomSelect.Option
                      key={`${format.provider}-${"delimiter" in format ? format.delimiter : "default"}`}
                      className="flex items-center gap-2"
                      value={format}
                    >
                      <span className="truncate">{t(format.i18n_title)}</span>
                    </CustomSelect.Option>
                  ))}
                </CustomSelect>
              )}
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div className="flex flex-col gap-0.5">
              <p className="text-13 text-secondary">
                {t("workspace_settings.settings.exports.project_csv.include_work_items")}
              </p>
              <p className="text-11 text-tertiary">
                {t("workspace_settings.settings.exports.project_csv.include_work_items_hint")}
              </p>
            </div>
            <Controller
              control={control}
              name="includeWorkItems"
              render={({ field: { value, onChange } }) => (
                <ToggleSwitch value={value} onChange={onChange} disabled={!isMember} />
              )}
            />
          </div>
          <Button
            type="submit"
            variant="primary"
            disabled={!hasProjects || !isMember || exportLoading}
            loading={exportLoading}
          >
            {includeWorkItems
              ? t("workspace_settings.settings.exports.project_csv.export_full_button")
              : t("workspace_settings.settings.exports.project_csv.export_button")}
          </Button>
        </form>
      }
    />
  );
});
