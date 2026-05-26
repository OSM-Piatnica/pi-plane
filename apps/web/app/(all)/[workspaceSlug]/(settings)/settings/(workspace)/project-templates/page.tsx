import { useState } from "react";
import { Controller, FormProvider, useForm, useWatch } from "react-hook-form";
import { observer } from "mobx-react";
import useSWR, { useSWRConfig } from "swr";
import { EUserPermissions, EUserPermissionsLevel, NETWORK_CHOICES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EModalPosition, EModalWidth, CustomSelect, Input, ModalCore, TextArea } from "@plane/ui";
import { ProjectTemplateSelectField } from "./project-template-select-field";
import type { TProjectTemplate } from "@plane/types";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { LogoSpinner } from "@/components/common/logo-spinner";
import { PageHead } from "@/components/core/page-title";
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
import { CreateProjectModal } from "@/components/project/create-project-modal";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { useUserPermissions } from "@/hooks/store/user";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { ProjectTemplateService } from "@/services/project-template.service";
import type { Route } from "./+types/page";
import { FeatureTogglesEditor } from "./feature-toggles-editor";
import { ProjectTemplatesSettingsHeader } from "./header";
import { LabelTemplatesEditor } from "./label-templates-editor";
import { DEFAULT_FEATURE_TOGGLES } from "./project-template-form.types";
import type { TProjectTemplateFormFields } from "./project-template-form.types";
import { buildProjectTemplatePayloadFromFormValues } from "./project-template-payload-helpers";
import { ProjectTemplateCoverField } from "./project-template-cover-field";
import { StateTemplatesEditor } from "./state-templates-editor";
import { WorkItemTypesTemplateEditor } from "./work-item-types-template-editor";

const service = new ProjectTemplateService();

const TEMPLATE_FORM_DEFAULTS: TProjectTemplateFormFields = {
  templateName: "",
  templateNote: "",
  projectName: "",
  projectIdentifier: "",
  projectDescription: "",
  projectLeadId: null,
  defaultAssigneeId: null,
  coverImageUrl: "",
  startDate: null,
  targetDate: null,
  features: { ...DEFAULT_FEATURE_TOGGLES },
  stateTemplates: [],
  labelTemplates: [],
  epicEnabled: false,
  taskCustomProperties: [],
  epicCustomProperties: [],
  additionalWorkItemTypes: [],
  network: 2,
};

function ProjectTemplatesPage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const { currentWorkspace } = useWorkspace();
  const { mutate } = useSWRConfig();
  const canManage = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );
  const { data: templates, isLoading } = useSWR(
    canManage && workspaceSlug ? `PROJECT_TEMPLATE_LIST_${workspaceSlug}` : null,
    () => service.list(workspaceSlug)
  );

  const [createTemplateModalOpen, setCreateTemplateModalOpen] = useState(false);
  const [createProjectModalOpen, setCreateProjectModalOpen] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const form = useForm<TProjectTemplateFormFields>({
    defaultValues: TEMPLATE_FORM_DEFAULTS,
  });
  const {
    handleSubmit,
    control,
    reset,
    formState: { isSubmitting, errors },
  } = form;

  const issueTypesFeatureEnabled = useWatch({
    control,
    name: "features.is_issue_type_enabled",
    defaultValue: DEFAULT_FEATURE_TOGGLES.is_issue_type_enabled,
  });

  const pageTitle = currentWorkspace?.name
    ? `${currentWorkspace.name} - ${t("workspace_settings.settings.project_templates.title")}`
    : undefined;

  const handleUseTemplate = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setCreateProjectModalOpen(true);
  };

  const onSubmit = handleSubmit(async (values) => {
    if (!values.templateName.trim()) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("error"),
        message: t("workspace_settings.settings.project_templates.form.name_required"),
      });
      return;
    }
    setSaving(true);
    try {
      await service.create(workspaceSlug, {
        name: values.templateName.trim(),
        description: values.templateNote,
        payload: buildProjectTemplatePayloadFromFormValues(values),
      });
      await mutate(`PROJECT_TEMPLATE_LIST_${workspaceSlug}`);
      setCreateTemplateModalOpen(false);
      reset(TEMPLATE_FORM_DEFAULTS);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("workspace_settings.settings.project_templates.toasts.created.title"),
        message: t("workspace_settings.settings.project_templates.toasts.created.message"),
      });
    } catch (e) {
      console.error(e);
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("workspace_settings.settings.project_templates.toasts.create_failed.title"),
        message: t("workspace_settings.settings.project_templates.toasts.create_failed.message"),
      });
    } finally {
      setSaving(false);
    }
  });

  const onDelete = async (id: string) => {
    if (!window.confirm(t("workspace_settings.settings.project_templates.delete_confirm"))) return;
    try {
      await service.remove(workspaceSlug, id);
      await mutate(`PROJECT_TEMPLATE_LIST_${workspaceSlug}`);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("workspace_settings.settings.project_templates.toasts.deleted.title"),
        message: t("workspace_settings.settings.project_templates.toasts.deleted.message"),
      });
    } catch (e) {
      console.error(e);
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("workspace_settings.settings.project_templates.toasts.delete_failed.title"),
        message: t("workspace_settings.settings.project_templates.toasts.delete_failed.message"),
      });
    }
  };

  if (!canManage) {
    return <NotAuthorizedView section="settings" className="h-auto" />;
  }

  return (
    <FormProvider {...form}>
      <SettingsContentWrapper header={<ProjectTemplatesSettingsHeader />}>
        <PageHead title={pageTitle} />
        <ModalCore
          isOpen={createTemplateModalOpen}
          handleClose={() => setCreateTemplateModalOpen(false)}
          position={EModalPosition.CENTER}
          width={EModalWidth.XXL}
        >
          <form onSubmit={onSubmit} className="flex max-h-[min(90vh,860px)] flex-col" id="project-template-create-form">
            <div className="flex-shrink-0 px-5 pt-5">
              <h3 className="text-h3-medium text-primary">
                {t("workspace_settings.settings.project_templates.add_template")}
              </h3>
              <p className="pt-1 pb-4 text-13 text-tertiary">
                {t("workspace_settings.settings.project_templates.form.modal_intro")}
              </p>
            </div>

            <div className="flex-shrink-0 overflow-visible px-5 pb-3">
              <ProjectTemplateCoverField control={control} workspaceSlug={workspaceSlug} />
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-5">
              <div className="space-y-6 pb-5">
                <section className="space-y-3">
                  <h4 className="text-12 font-semibold tracking-wide text-tertiary uppercase">
                    {t("workspace_settings.settings.project_templates.form.section_template")}
                  </h4>
                  <div>
                    <label className="text-12 text-tertiary" htmlFor="project-template-name">
                      {t("workspace_settings.settings.project_templates.form.template_name_label")}
                    </label>
                    <Controller
                      name="templateName"
                      control={control}
                      render={({ field }) => (
                        <Input
                          id="project-template-name"
                          className="mt-1 w-full"
                          value={field.value}
                          onChange={field.onChange}
                          placeholder={t(
                            "workspace_settings.settings.project_templates.form.template_name_placeholder"
                          )}
                        />
                      )}
                    />
                  </div>
                  <div>
                    <label className="text-12 text-tertiary" htmlFor="project-template-note">
                      {t("workspace_settings.settings.project_templates.form.template_note_label")}
                    </label>
                    <Controller
                      name="templateNote"
                      control={control}
                      render={({ field }) => (
                        <TextArea
                          id="project-template-note"
                          className="mt-1 min-h-[80px] w-full resize-y"
                          value={field.value}
                          onChange={field.onChange}
                          rows={3}
                          placeholder={t(
                            "workspace_settings.settings.project_templates.form.template_note_placeholder"
                          )}
                        />
                      )}
                    />
                  </div>
                </section>

                <section className="space-y-3">
                  <h4 className="text-12 font-semibold tracking-wide text-tertiary uppercase">
                    {t("workspace_settings.settings.project_templates.form.section_properties")}
                  </h4>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-12 text-tertiary" htmlFor="project-template-default-name">
                        {t("workspace_settings.settings.project_templates.form.default_project_name")}
                      </label>
                      <Controller
                        name="projectName"
                        control={control}
                        render={({ field }) => (
                          <Input
                            id="project-template-default-name"
                            className="mt-1 w-full"
                            value={field.value}
                            onChange={field.onChange}
                            placeholder={t(
                              "workspace_settings.settings.project_templates.form.default_project_name_placeholder"
                            )}
                          />
                        )}
                      />
                    </div>
                    <div>
                      <label className="text-12 text-tertiary" htmlFor="project-template-network">
                        {t("workspace_settings.settings.project_templates.form.default_visibility")}
                      </label>
                      <Controller
                        name="network"
                        control={control}
                        render={({ field: { value, onChange } }) => (
                          <div className="mt-1">
                            <ProjectTemplateSelectField
                              value={value}
                              onChange={onChange}
                              label={t(
                                NETWORK_CHOICES.find((network) => network.key === value)?.i18n_label ??
                                  NETWORK_CHOICES[0].i18n_label
                              )}
                            >
                              {NETWORK_CHOICES.map((network) => (
                                <CustomSelect.Option key={network.key} value={network.key}>
                                  {t(network.i18n_label)}
                                </CustomSelect.Option>
                              ))}
                            </ProjectTemplateSelectField>
                          </div>
                        )}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-12 text-tertiary">
                        {t("workspace_settings.settings.project_templates.form.default_lead")}
                      </label>
                      <div className="mt-1 h-8">
                        <Controller
                          name="projectLeadId"
                          control={control}
                          render={({ field }) => (
                            <MemberDropdown
                              value={field.value}
                              onChange={(value) => field.onChange(value || null)}
                              placeholder={t("workspace_settings.settings.project_templates.form.default_lead")}
                              multiple={false}
                              buttonVariant="border-with-text"
                            />
                          )}
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-12 text-tertiary">
                        {t("workspace_settings.settings.project_templates.form.default_assignee")}
                      </label>
                      <div className="mt-1 h-8">
                        <Controller
                          name="defaultAssigneeId"
                          control={control}
                          render={({ field }) => (
                            <MemberDropdown
                              value={field.value}
                              onChange={(value) => field.onChange(value || null)}
                              placeholder={t("workspace_settings.settings.project_templates.form.default_assignee")}
                              multiple={false}
                              buttonVariant="border-with-text"
                            />
                          )}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div>
                      <label className="text-12 text-tertiary" htmlFor="project-template-default-start">
                        {t("workspace_settings.settings.project_templates.form.default_start_date")}
                      </label>
                      <Controller
                        name="startDate"
                        control={control}
                        render={({ field }) => (
                          <Input
                            id="project-template-default-start"
                            className="mt-1 w-full"
                            type="date"
                            value={field.value ?? ""}
                            onChange={(e) => field.onChange(e.target.value || null)}
                          />
                        )}
                      />
                    </div>
                    <div>
                      <label className="text-12 text-tertiary" htmlFor="project-template-default-target">
                        {t("workspace_settings.settings.project_templates.form.default_target_date")}
                      </label>
                      <Controller
                        name="targetDate"
                        control={control}
                        render={({ field }) => (
                          <Input
                            id="project-template-default-target"
                            className="mt-1 w-full"
                            type="date"
                            value={field.value ?? ""}
                            onChange={(e) => field.onChange(e.target.value || null)}
                          />
                        )}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-12 text-tertiary" htmlFor="project-template-default-identifier">
                      {t("workspace_settings.settings.project_templates.form.default_project_identifier")}
                    </label>
                    <Controller
                      name="projectIdentifier"
                      control={control}
                      rules={{
                        maxLength: {
                          value: 10,
                          message: t("workspace_settings.settings.project_templates.form.identifier_max_char"),
                        },
                        validate: (value) =>
                          !value ||
                          /^[A-Z0-9]+$/.test(value.toUpperCase()) ||
                          t("workspace_settings.settings.project_templates.form.identifier_invalid"),
                      }}
                      render={({ field }) => (
                        <Input
                          id="project-template-default-identifier"
                          className="mt-1 w-full uppercase"
                          value={field.value}
                          onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                          placeholder={t(
                            "workspace_settings.settings.project_templates.form.default_project_identifier_placeholder"
                          )}
                          hasError={Boolean(errors.projectIdentifier)}
                        />
                      )}
                    />
                    <span className="text-11 text-danger-primary">{errors.projectIdentifier?.message}</span>
                  </div>
                  <div>
                    <label className="text-12 text-tertiary" htmlFor="project-template-default-description">
                      {t("workspace_settings.settings.project_templates.form.default_project_description")}
                    </label>
                    <Controller
                      name="projectDescription"
                      control={control}
                      render={({ field }) => (
                        <TextArea
                          id="project-template-default-description"
                          className="mt-1 min-h-[80px] w-full resize-y"
                          value={field.value}
                          onChange={field.onChange}
                          rows={3}
                          placeholder={t(
                            "workspace_settings.settings.project_templates.form.default_project_description_placeholder"
                          )}
                        />
                      )}
                    />
                  </div>
                </section>

                <section className="space-y-3">
                  <div>
                    <h4 className="text-12 font-semibold tracking-wide text-tertiary uppercase">
                      {t("workspace_settings.settings.project_templates.form.section_features")}
                    </h4>
                    <p className="text-12 text-tertiary">
                      {t("workspace_settings.settings.project_templates.form.section_features_hint")}
                    </p>
                  </div>
                  <Controller
                    name="features"
                    control={control}
                    render={({ field }) => <FeatureTogglesEditor value={field.value} onChange={field.onChange} />}
                  />
                </section>

                <section className="space-y-3">
                  <div>
                    <h4 className="text-12 font-semibold tracking-wide text-tertiary uppercase">
                      {t("workspace_settings.settings.project_templates.form.section_work_item_types")}
                    </h4>
                    <p className="text-12 text-tertiary">
                      {t("workspace_settings.settings.project_templates.form.section_work_item_types_hint")}
                    </p>
                  </div>
                  <Controller
                    name="epicEnabled"
                    control={control}
                    render={({ field: epicEnabledField }) => (
                      <Controller
                        name="taskCustomProperties"
                        control={control}
                        render={({ field: taskField }) => (
                          <Controller
                            name="epicCustomProperties"
                            control={control}
                            render={({ field: epicField }) => (
                              <Controller
                                name="additionalWorkItemTypes"
                                control={control}
                                render={({ field: addField }) => (
                                  <WorkItemTypesTemplateEditor
                                    enabled={Boolean(issueTypesFeatureEnabled)}
                                    epicEnabled={epicEnabledField.value}
                                    onEpicEnabledChange={epicEnabledField.onChange}
                                    taskCustomProperties={taskField.value}
                                    epicCustomProperties={epicField.value}
                                    additionalWorkItemTypes={addField.value}
                                    onChangeTask={taskField.onChange}
                                    onChangeEpic={epicField.onChange}
                                    onChangeAdditional={addField.onChange}
                                  />
                                )}
                              />
                            )}
                          />
                        )}
                      />
                    )}
                  />
                </section>

                <section className="space-y-3">
                  <div>
                    <h4 className="text-12 font-semibold tracking-wide text-tertiary uppercase">
                      {t("workspace_settings.settings.project_templates.form.section_states")}
                    </h4>
                    <p className="text-12 text-tertiary">
                      {t("workspace_settings.settings.project_templates.form.section_states_hint")}
                    </p>
                  </div>
                  <Controller
                    name="stateTemplates"
                    control={control}
                    render={({ field }) => <StateTemplatesEditor value={field.value} onChange={field.onChange} />}
                  />
                </section>

                <section className="space-y-3">
                  <div>
                    <h4 className="text-12 font-semibold tracking-wide text-tertiary uppercase">
                      {t("workspace_settings.settings.project_templates.form.section_labels")}
                    </h4>
                    <p className="text-12 text-tertiary">
                      {t("workspace_settings.settings.project_templates.form.section_labels_hint")}
                    </p>
                  </div>
                  <Controller
                    name="labelTemplates"
                    control={control}
                    render={({ field }) => <LabelTemplatesEditor value={field.value} onChange={field.onChange} />}
                  />
                </section>
              </div>
            </div>

            <div className="flex flex-shrink-0 justify-end gap-2 border-t border-subtle px-5 py-3">
              <Button type="button" variant="secondary" onClick={() => setCreateTemplateModalOpen(false)}>
                {t("cancel")}
              </Button>
              <Button type="submit" variant="primary" disabled={saving || isSubmitting} loading={saving}>
                {t("add")}
              </Button>
            </div>
          </form>
        </ModalCore>

        <CreateProjectModal
          isOpen={createProjectModalOpen}
          onClose={() => {
            setCreateProjectModalOpen(false);
            setSelectedTemplateId(null);
          }}
          workspaceSlug={workspaceSlug}
          templateId={selectedTemplateId ?? undefined}
        />

        <div className="w-full">
          <SettingsHeading
            title={t("workspace_settings.settings.project_templates.title")}
            description={t("workspace_settings.settings.project_templates.description")}
            control={
              <Button variant="primary" size="lg" onClick={() => setCreateTemplateModalOpen(true)}>
                {t("workspace_settings.settings.project_templates.add_template")}
              </Button>
            }
          />
          {isLoading || !templates ? (
            <div className="flex justify-center py-8">
              <LogoSpinner />
            </div>
          ) : !templates || templates.length === 0 ? (
            <p className="py-4 text-13 text-tertiary">{t("no_data_yet")}</p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
              {(templates as TProjectTemplate[]).map((template) => (
                <div key={template.id} className="rounded-md border border-subtle bg-surface-1 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="text-14 font-semibold text-primary">{template.name}</h4>
                      <p className="pt-1 text-12 text-tertiary">
                        {template.description ||
                          t("workspace_settings.settings.project_templates.table.no_description")}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="secondary" size="sm" onClick={() => handleUseTemplate(template.id)}>
                        {t("workspace_settings.settings.project_templates.table.use_template")}
                      </Button>
                      <Button variant="error-outline" size="sm" onClick={() => onDelete(template.id)}>
                        {t("remove")}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </SettingsContentWrapper>
    </FormProvider>
  );
}

export default observer(ProjectTemplatesPage);
