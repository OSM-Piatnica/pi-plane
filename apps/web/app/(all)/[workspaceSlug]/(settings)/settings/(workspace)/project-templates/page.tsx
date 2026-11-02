/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { Controller, FormProvider, useForm, useWatch } from "react-hook-form";
import { observer } from "mobx-react";
import useSWR, { useSWRConfig } from "swr";
import { EUserPermissions, EUserPermissionsLevel, NETWORK_CHOICES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogClose,
  DialogCloseGroup,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { Field } from "@makeplane/propel/components/field";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import { CloseOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { ProjectTemplateSelectField } from "./project-template-select-field";
import type { TProjectTemplate } from "@plane/types";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { LogoSpinner } from "@/components/common/logo-spinner";
import { PageHead } from "@/components/core/page-title";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { CreateProjectModal } from "@/components/project/create-project-modal";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { useUserPermissions } from "@/hooks/store/user";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { ProjectTemplateService } from "@/services/project-template.service";
import { userGroupService } from "@/services/user-group.service";
import { getGroupPaths } from "@/helpers/project-template-groups";
import type { Route } from "./+types/page";
import { FeatureTogglesEditor } from "./feature-toggles-editor";
import { GroupsTemplateEditor } from "./groups-template-editor";
import { ProjectTemplatesSettingsHeader } from "./header";
import { LabelTemplatesEditor } from "./label-templates-editor";
import { DEFAULT_FEATURE_TOGGLES } from "./project-template-form.types";
import type { TProjectTemplateFormFields } from "./project-template-form.types";
import {
  buildProjectTemplatePayloadFromFormValues,
  mapProjectTemplateToFormValues,
} from "./project-template-payload-helpers";
import {
  buildUniqueTemplateName,
  downloadTemplateAsJson,
  isValidTemplateFile,
  MAX_TEMPLATE_FILE_SIZE_BYTES,
  ProjectTemplateFileError,
  readTemplateFromJson,
} from "./project-template-file-helpers";
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
  groups: [],
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

  // the workspace's groups, for the "Groups as members" section and the paths written next to their ids
  const { data: groups } = useSWR(canManage && workspaceSlug ? `USER_GROUPS_${workspaceSlug}` : null, () =>
    userGroupService.list(workspaceSlug)
  );

  const [createTemplateModalOpen, setCreateTemplateModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [createProjectModalOpen, setCreateProjectModalOpen] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const uploadInputRef = useRef<HTMLInputElement>(null);
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

  // react-doctor-disable-next-line no-event-handler -- the modal is closed from several places (submit, cancel, onOpenChange), so resetting must follow the state itself
  useEffect(() => {
    if (!createTemplateModalOpen) {
      reset(TEMPLATE_FORM_DEFAULTS);
      setEditingId(null);
    }
  }, [createTemplateModalOpen, reset]);

  const openCreate = () => {
    reset(TEMPLATE_FORM_DEFAULTS);
    setEditingId(null);
    setCreateTemplateModalOpen(true);
  };

  const openEdit = (template: TProjectTemplate) => {
    reset(mapProjectTemplateToFormValues(template));
    setEditingId(template.id);
    setCreateTemplateModalOpen(true);
  };

  const pageTitle = currentWorkspace?.name
    ? `${currentWorkspace.name} - ${t("workspace_settings.settings.project_templates.title")}`
    : undefined;

  const handleUseTemplate = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setCreateProjectModalOpen(true);
  };

  const handleDownloadTemplate = (template: TProjectTemplate) => {
    try {
      downloadTemplateAsJson(template);
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
        title: t("error"),
        message: t("workspace_settings.settings.project_templates.toasts.download_failed.message"),
      });
    }
  };

  const handleUploadTemplate = async (file: File) => {
    if (!isValidTemplateFile(file)) {
      setToast({
        type: "error",
        title: t("error"),
        message: t("workspace_settings.settings.project_templates.upload_invalid_file"),
      });
      return;
    }
    if (file.size > MAX_TEMPLATE_FILE_SIZE_BYTES) {
      setToast({
        type: "error",
        title: t("error"),
        message: t("workspace_settings.settings.project_templates.upload_too_large", {
          size: Math.round(MAX_TEMPLATE_FILE_SIZE_BYTES / (1024 * 1024)),
        }),
      });
      return;
    }

    setUploading(true);
    try {
      const parsed = await readTemplateFromJson(file);
      const existingNames = ((templates as TProjectTemplate[] | undefined) ?? []).map((item) => item.name);
      const desired = parsed.name || file.name.replace(/\.json$/i, "");
      const name = buildUniqueTemplateName(desired, existingNames, t("app_text.project_templates.imported_template"));
      const renamed = name !== desired.trim();

      const created = await service.create(workspaceSlug, {
        name,
        description: parsed.description,
        payload: parsed.payload,
      });
      await mutate(`PROJECT_TEMPLATE_LIST_${workspaceSlug}`);

      // groups are matched by path; the ones this workspace does not have are left out and named here
      const notFound = (created.unmatched_groups ?? []).map((item) => item.path || item.group || "").filter(Boolean);
      if (notFound.length > 0) {
        setToast({
          type: "warning",
          title: t("warning"),
          message: t("workspace_settings.settings.project_templates.toasts.uploaded_groups_not_found.message", {
            name,
            groups: notFound.join(", "),
          }),
        });
        return;
      }

      setToast({
        type: renamed ? "warning" : "success",
        title: renamed ? t("warning") : t("success"),
        message: renamed
          ? t("workspace_settings.settings.project_templates.toasts.uploaded_renamed.message", { name })
          : t("workspace_settings.settings.project_templates.toasts.uploaded.message", { name }),
      });
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
        title: t("error"),
        message:
          e instanceof ProjectTemplateFileError
            ? t("workspace_settings.settings.project_templates.upload_invalid_file")
            : t("workspace_settings.settings.project_templates.toasts.upload_failed.message"),
      });
    } finally {
      setUploading(false);
      if (uploadInputRef.current) uploadInputRef.current.value = "";
    }
  };

  const onSubmit = handleSubmit(async (values) => {
    if (!values.templateName.trim()) {
      setToast({
        type: "error",
        title: t("error"),
        message: t("workspace_settings.settings.project_templates.form.name_required"),
      });
      return;
    }
    setSaving(true);
    try {
      const body = {
        name: values.templateName.trim(),
        description: values.templateNote,
        payload: buildProjectTemplatePayloadFromFormValues(values, getGroupPaths(groups ?? [])),
      };
      if (editingId) {
        await service.update(workspaceSlug, editingId, body);
      } else {
        await service.create(workspaceSlug, body);
      }
      await mutate(`PROJECT_TEMPLATE_LIST_${workspaceSlug}`);
      setCreateTemplateModalOpen(false);
      setToast({
        type: "success",
        title: t("workspace_settings.settings.project_templates.toasts.saved.title"),
        message: t("workspace_settings.settings.project_templates.toasts.saved.message"),
      });
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
        title: t("workspace_settings.settings.project_templates.toasts.save_failed.title"),
        message: t("workspace_settings.settings.project_templates.toasts.save_failed.message"),
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
        type: "success",
        title: t("workspace_settings.settings.project_templates.toasts.deleted.title"),
        message: t("workspace_settings.settings.project_templates.toasts.deleted.message"),
      });
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
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
        <Dialog
          open={createTemplateModalOpen}
          onOpenChange={(open) => {
            if (!open) setCreateTemplateModalOpen(false);
          }}
        >
          <DialogContent size="xl">
            <DialogCloseGroup>
              <IconButton
                variant="ghost"
                size="xs"
                aria-label={t("close")}
                icon={<Icon icon={CloseOutline} />}
                render={<DialogClose />}
              />
            </DialogCloseGroup>
            <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col" id="project-template-create-form">
              <DialogMain>
                <DialogHeader>
                  <DialogHeading>
                    <DialogTitle>
                      {editingId
                        ? t("workspace_settings.settings.project_templates.edit_template")
                        : t("workspace_settings.settings.project_templates.add_template")}
                    </DialogTitle>
                    <DialogDescription>
                      {t("workspace_settings.settings.project_templates.form.modal_intro")}
                    </DialogDescription>
                  </DialogHeading>
                </DialogHeader>
                <DialogBody>
                  <div className="pb-3">
                    <ProjectTemplateCoverField control={control} workspaceSlug={workspaceSlug} />
                  </div>
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
                            <Field name="project-template-name">
                              <InputGroup size="lg">
                                <Input
                                  size="lg"
                                  id="project-template-name"
                                  value={field.value}
                                  onChange={field.onChange}
                                  placeholder={t(
                                    "workspace_settings.settings.project_templates.form.template_name_placeholder"
                                  )}
                                />
                              </InputGroup>
                            </Field>
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
                            <Field name="project-template-note">
                              <TextAreaGroup resize="vertical">
                                <TextArea
                                  size="lg"
                                  surface="field"
                                  id="project-template-note"
                                  value={field.value}
                                  onChange={field.onChange}
                                  rows={3}
                                  placeholder={t(
                                    "workspace_settings.settings.project_templates.form.template_note_placeholder"
                                  )}
                                />
                              </TextAreaGroup>
                            </Field>
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
                              <Field name="project-template-default-name">
                                <InputGroup size="lg">
                                  <Input
                                    size="lg"
                                    id="project-template-default-name"
                                    value={field.value}
                                    onChange={field.onChange}
                                    placeholder={t(
                                      "workspace_settings.settings.project_templates.form.default_project_name_placeholder"
                                    )}
                                  />
                                </InputGroup>
                              </Field>
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
                                  options={NETWORK_CHOICES.map((network) => ({
                                    value: network.key,
                                    label: t(network.i18n_label),
                                  }))}
                                />
                              </div>
                            )}
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                        <div>
                          <span id="project-template-default-lead-label" className="text-12 text-tertiary">
                            {t("workspace_settings.settings.project_templates.form.default_lead")}
                          </span>
                          <div className="mt-1 h-8" role="group" aria-labelledby="project-template-default-lead-label">
                            <Controller
                              name="projectLeadId"
                              control={control}
                              render={({ field }) => (
                                <MemberSelect
                                  value={field.value}
                                  onChange={(value) => field.onChange(value || null)}
                                  placeholder={t("workspace_settings.settings.project_templates.form.default_lead")}
                                  variant="select-lg"
                                  clearable
                                />
                              )}
                            />
                          </div>
                        </div>
                        <div>
                          <span id="project-template-default-assignee-label" className="text-12 text-tertiary">
                            {t("workspace_settings.settings.project_templates.form.default_assignee")}
                          </span>
                          <div
                            className="mt-1 h-8"
                            role="group"
                            aria-labelledby="project-template-default-assignee-label"
                          >
                            <Controller
                              name="defaultAssigneeId"
                              control={control}
                              render={({ field }) => (
                                <MemberSelect
                                  value={field.value}
                                  onChange={(value) => field.onChange(value || null)}
                                  placeholder={t("workspace_settings.settings.project_templates.form.default_assignee")}
                                  variant="select-lg"
                                  clearable
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
                              <Field name="project-template-default-start">
                                <InputGroup size="lg">
                                  <Input
                                    size="lg"
                                    id="project-template-default-start"
                                    type="date"
                                    value={field.value ?? ""}
                                    onChange={(e) => field.onChange(e.target.value || null)}
                                  />
                                </InputGroup>
                              </Field>
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
                              <Field name="project-template-default-target">
                                <InputGroup size="lg">
                                  <Input
                                    size="lg"
                                    id="project-template-default-target"
                                    type="date"
                                    value={field.value ?? ""}
                                    onChange={(e) => field.onChange(e.target.value || null)}
                                  />
                                </InputGroup>
                              </Field>
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
                            <Field
                              name="project-template-default-identifier"
                              invalid={Boolean(errors.projectIdentifier)}
                            >
                              <InputGroup size="lg">
                                <Input
                                  size="lg"
                                  id="project-template-default-identifier"
                                  value={field.value}
                                  onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                                  placeholder={t(
                                    "workspace_settings.settings.project_templates.form.default_project_identifier_placeholder"
                                  )}
                                />
                              </InputGroup>
                            </Field>
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
                            <Field name="project-template-default-description">
                              <TextAreaGroup resize="vertical">
                                <TextArea
                                  size="lg"
                                  surface="field"
                                  id="project-template-default-description"
                                  value={field.value}
                                  onChange={field.onChange}
                                  rows={3}
                                  placeholder={t(
                                    "workspace_settings.settings.project_templates.form.default_project_description_placeholder"
                                  )}
                                />
                              </TextAreaGroup>
                            </Field>
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

                    <section className="space-y-3">
                      <div>
                        <h4 className="text-12 font-semibold tracking-wide text-tertiary uppercase">
                          {t("workspace_settings.settings.project_templates.form.section_groups")}
                        </h4>
                        <p className="text-12 text-tertiary">
                          {t("workspace_settings.settings.project_templates.form.section_groups_hint")}
                        </p>
                      </div>
                      <Controller
                        name="groups"
                        control={control}
                        render={({ field }) => (
                          <GroupsTemplateEditor value={field.value} onChange={field.onChange} groups={groups} />
                        )}
                      />
                    </section>
                  </div>
                </DialogBody>
              </DialogMain>
              <DialogActions>
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  stretch="auto"
                  label={t("cancel")}
                  onClick={() => setCreateTemplateModalOpen(false)}
                />
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  stretch="auto"
                  label={editingId ? t("save_changes") : t("add")}
                  disabled={saving || isSubmitting}
                  loading={saving}
                />
              </DialogActions>
            </form>
          </DialogContent>
        </Dialog>

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
              <div className="flex items-center gap-2">
                <input
                  ref={uploadInputRef}
                  type="file"
                  accept=".json,application/json"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void handleUploadTemplate(file);
                  }}
                />
                <Button
                  stretch="auto"
                  variant="secondary"
                  size="lg"
                  onClick={() => uploadInputRef.current?.click()}
                  disabled={uploading}
                  loading={uploading}
                  label={t("workspace_settings.settings.project_templates.upload_template")}
                />
                <Button
                  stretch="auto"
                  variant="primary"
                  size="lg"
                  onClick={openCreate}
                  label={t("workspace_settings.settings.project_templates.add_template")}
                />
              </div>
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
                      <Button
                        stretch="auto"
                        variant="secondary"
                        size="sm"
                        onClick={() => openEdit(template)}
                        label={t("edit")}
                      />
                      <Button
                        stretch="auto"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleUseTemplate(template.id)}
                        label={t("workspace_settings.settings.project_templates.table.use_template")}
                      />
                      <Button
                        stretch="auto"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleDownloadTemplate(template)}
                        label={t("workspace_settings.settings.project_templates.table.download_template")}
                      />
                      <Button
                        stretch="auto"
                        variant="danger-outline"
                        size="sm"
                        onClick={() => onDelete(template.id)}
                        label={t("remove")}
                      />
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
