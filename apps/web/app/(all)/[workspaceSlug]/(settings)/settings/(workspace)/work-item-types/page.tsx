/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { Controller, FormProvider, useForm } from "react-hook-form";
import { observer } from "mobx-react";
import useSWR, { useSWRConfig } from "swr";
import { Layers } from "lucide-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import type { ChangeHandlerPayload } from "@plane/blocks/emoji-icon-picker";
import { EmojiPicker, Logo } from "@plane/blocks/emoji-icon-picker";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Dialog, DialogBody, DialogContent, DialogMain } from "@makeplane/propel/components/dialog";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import { setToast } from "@plane/blocks/toast";
import { Switch } from "@makeplane/propel/components/switch";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { TIssueType } from "@plane/types";
import { getIssueTypeKind, isSystemManagedKind, isSystemManagedType } from "@plane/utils";
import { PageHead } from "@/components/core/page-title";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { ProjectSelect } from "@/components/dropdowns/project/project-select";
import { SwitcherIcon } from "@/components/common/switcher-label";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { useUserPermissions } from "@/hooks/store/user";
import { useProject } from "@/hooks/store/use-project";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { IssueTypeService } from "@/services/issue-type.service";
import { LogoSpinner } from "@/components/common/logo-spinner";
import type { Route } from "./+types/page";
import { WorkItemTypesSettingsHeader } from "./header";
import { WorkItemTypePropertyEditor } from "./work-item-type-property-editor";
import { DEFAULT_WORK_ITEM_TYPE_FORM, type TWorkItemTypeFormFields } from "./work-item-type-form.types";
import {
  buildIssueTypePayloadFromForm,
  canToggleEpicKind,
  getKindBadgeKey,
  mapIssueTypeToFormValues,
} from "./work-item-type-payload-helpers";

const service = new IssueTypeService();

function WorkItemTypesPage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const { currentWorkspace } = useWorkspace();
  const { getProjectById } = useProject();
  const { mutate } = useSWRConfig();

  const canManage = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );

  const listKey = canManage && workspaceSlug ? `ISSUE_TYPES_${workspaceSlug}` : null;
  const { data: issueTypes, isLoading } = useSWR(listKey, () => service.listWorkspaceTypes(workspaceSlug));

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [logoPickerOpen, setLogoPickerOpen] = useState(false);

  const form = useForm<TWorkItemTypeFormFields>({
    defaultValues: DEFAULT_WORK_ITEM_TYPE_FORM,
  });

  const { handleSubmit, control, reset, watch, setValue, formState } = form;
  const properties = watch("properties");
  // the kind of the type in the form: set by the server, shown but never edited here
  const editingKind = getIssueTypeKind(issueTypes?.find((row) => row.id === editingId));
  const isEditingSystemManaged = isSystemManagedKind(editingKind);

  // react-doctor-disable-next-line no-event-handler -- modalOpen is closed from several places (submit, cancel, modal onOpenChange), so one effect keeps the reset in sync
  useEffect(() => {
    if (!modalOpen) {
      reset(DEFAULT_WORK_ITEM_TYPE_FORM);
      setEditingId(null);
    }
  }, [modalOpen, reset]);

  const openCreate = () => {
    reset(DEFAULT_WORK_ITEM_TYPE_FORM);
    setEditingId(null);
    setModalOpen(true);
  };

  const openEdit = (row: TIssueType) => {
    reset(mapIssueTypeToFormValues(row));
    setEditingId(row.id);
    setModalOpen(true);
  };

  const pageTitle = currentWorkspace?.name
    ? `${currentWorkspace.name} - ${t("workspace_settings.settings.work_item_types.title")}`
    : undefined;

  const onSubmit = handleSubmit(async (values) => {
    if (!values.name.trim()) {
      setToast({
        type: "error",
        title: t("error"),
        message: t("workspace_settings.settings.work_item_types.form.name_required"),
      });
      return;
    }
    const payload = buildIssueTypePayloadFromForm(values, editingKind);
    setSaving(true);
    try {
      if (editingId) {
        await service.updateWorkspaceType(workspaceSlug, editingId, payload);
      } else {
        await service.createWorkspaceType(workspaceSlug, payload);
      }
      await mutate(listKey);
      setModalOpen(false);
      setToast({
        type: "success",
        title: t("workspace_settings.settings.work_item_types.toasts.saved.title"),
        message: t("workspace_settings.settings.work_item_types.toasts.saved.message"),
      });
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
        title: t("workspace_settings.settings.work_item_types.toasts.save_failed.title"),
        message: t("workspace_settings.settings.work_item_types.toasts.save_failed.message"),
      });
    } finally {
      setSaving(false);
    }
  });

  const onToggleActive = async (row: TIssueType) => {
    if (isSystemManagedType(row)) return;
    try {
      await service.updateWorkspaceType(workspaceSlug, row.id, { is_active: !row.is_active });
      await mutate(listKey);
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
        title: t("error"),
        message: t("workspace_settings.settings.work_item_types.toasts.save_failed.message"),
      });
    }
  };

  const onDelete = async (row: TIssueType) => {
    if (isSystemManagedType(row)) return;
    const id = row.id;
    if (!window.confirm(t("workspace_settings.settings.work_item_types.delete_confirm"))) return;
    try {
      await service.removeWorkspaceType(workspaceSlug, id);
      await mutate(listKey);
      setToast({
        type: "success",
        title: t("workspace_settings.settings.work_item_types.toasts.deleted.title"),
        message: t("workspace_settings.settings.work_item_types.toasts.deleted.message"),
      });
    } catch (e) {
      console.error(e);
      setToast({
        type: "error",
        title: t("workspace_settings.settings.work_item_types.toasts.delete_failed.title"),
        message: t("workspace_settings.settings.work_item_types.toasts.delete_failed.message"),
      });
    }
  };

  if (!canManage) {
    return <NotAuthorizedView section="settings" className="h-auto" />;
  }

  return (
    <FormProvider {...form}>
      <SettingsContentWrapper header={<WorkItemTypesSettingsHeader />}>
        <PageHead title={pageTitle} />
        <Dialog
          open={modalOpen}
          onOpenChange={(open) => {
            if (!open) setModalOpen(false);
          }}
        >
          <DialogContent size="xl">
            <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
              <DialogMain>
                <DialogBody tabIndex={0}>
                  <div className="max-h-[min(90vh,920px)] p-1">
                    <h3 className="text-h3-medium text-primary">
                      {editingId
                        ? t("workspace_settings.settings.work_item_types.edit_type")
                        : t("workspace_settings.settings.work_item_types.add_type")}
                    </h3>
                    <p className="pt-1 pb-4 text-13 text-tertiary">
                      {t("workspace_settings.settings.work_item_types.form.modal_intro")}
                    </p>
                    <div className="space-y-4">
                      <div className="flex items-start gap-3">
                        <Controller
                          name="logoProps"
                          control={control}
                          render={({ field: { value, onChange } }) => (
                            <EmojiPicker
                              iconType="material"
                              closeOnSelect={false}
                              isOpen={logoPickerOpen}
                              handleToggle={(open: boolean) => setLogoPickerOpen(open)}
                              className="flex shrink-0 items-center justify-center"
                              buttonClassName="flex h-10 w-10 items-center justify-center rounded-md border border-subtle bg-surface-2"
                              label={<Logo logo={value} size={20} />}
                              onChange={(val: ChangeHandlerPayload) => {
                                let logoValue = {};
                                if (val?.type === "emoji") logoValue = { value: val.value };
                                else if (val?.type === "icon") logoValue = val.value;
                                onChange({
                                  in_use: val?.type,
                                  [val?.type]: logoValue,
                                });
                                setLogoPickerOpen(false);
                              }}
                              defaultIconColor={value?.in_use === "icon" ? value?.icon?.color : undefined}
                              defaultOpen={value?.in_use === "emoji" ? "emoji" : "icon"}
                            />
                          )}
                        />
                        <div className="min-w-0 flex-1 space-y-3">
                          <div>
                            <label className="mb-1 block text-12 text-tertiary" htmlFor="work-item-type-name">
                              {t("workspace_settings.settings.work_item_types.form.name_label")}
                            </label>
                            <Controller
                              name="name"
                              control={control}
                              render={({ field }) => (
                                <InputGroup size="lg">
                                  <Input
                                    size="lg"
                                    id="work-item-type-name"
                                    value={field.value}
                                    onChange={field.onChange}
                                  />
                                </InputGroup>
                              )}
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-12 text-tertiary" htmlFor="work-item-type-description">
                              {t("workspace_settings.settings.work_item_types.form.description_label")}
                            </label>
                            <Controller
                              name="description"
                              control={control}
                              render={({ field }) => (
                                <TextAreaGroup resize="vertical">
                                  <TextArea
                                    size="md"
                                    surface="field"
                                    id="work-item-type-description"
                                    rows={3}
                                    value={field.value}
                                    onChange={field.onChange}
                                  />
                                </TextAreaGroup>
                              )}
                            />
                          </div>
                        </div>
                      </div>
                      {isEditingSystemManaged ? (
                        <p className="rounded-md border border-subtle bg-surface-1 px-3 py-2 text-12 text-secondary">
                          {t("workspace_settings.settings.work_item_types.system_type_hint")}
                        </p>
                      ) : (
                        <>
                          <div className="flex flex-wrap items-center gap-6">
                            {canToggleEpicKind(editingKind) ? (
                              // react-doctor-disable-next-line label-has-associated-control -- the Switch is rendered inside the Controller render prop, so it is nested in this label
                              <label className="flex items-center gap-2 text-13 text-secondary">
                                <Controller
                                  name="isEpic"
                                  control={control}
                                  render={({ field }) => (
                                    <Switch checked={field.value} onCheckedChange={field.onChange} size="sm" />
                                  )}
                                />
                                {t("workspace_settings.settings.work_item_types.form.is_epic")}
                              </label>
                            ) : null}
                            {/* react-doctor-disable-next-line label-has-associated-control -- the Switch is rendered inside the Controller render prop, so it is nested in this label */}
                            <label className="flex items-center gap-2 text-13 text-secondary">
                              <Controller
                                name="isActive"
                                control={control}
                                render={({ field }) => (
                                  <Switch checked={field.value} onCheckedChange={field.onChange} size="sm" />
                                )}
                              />
                              {t("workspace_settings.settings.work_item_types.form.is_active")}
                            </label>
                          </div>
                          <div>
                            <span id="work-item-type-projects-label" className="block text-12 text-tertiary">
                              {t("workspace_settings.settings.work_item_types.form.projects_label")}
                            </span>
                            <p className="pt-0.5 pb-1 text-11 text-tertiary">
                              {t("workspace_settings.settings.work_item_types.form.projects_hint")}
                            </p>
                            <div
                              className="mt-1 h-8 max-w-md"
                              role="group"
                              aria-labelledby="work-item-type-projects-label"
                            >
                              <Controller
                                name="projectIds"
                                control={control}
                                render={({ field }) => (
                                  <ProjectSelect
                                    value={field.value}
                                    onChange={(ids) => field.onChange(ids)}
                                    multiple
                                    variant="select-md"
                                  />
                                )}
                              />
                            </div>
                          </div>
                        </>
                      )}
                      <div className="rounded-md border border-subtle bg-surface-1 p-3">
                        <h4 className="pb-2 text-14 font-medium text-primary">
                          {t("workspace_settings.settings.work_item_types.form.properties_heading")}
                        </h4>
                        <WorkItemTypePropertyEditor
                          properties={properties}
                          onChange={(next) => setValue("properties", next, { shouldDirty: true })}
                        />
                      </div>
                      <div className="flex justify-end gap-2 pt-2">
                        <Button
                          size="md"
                          stretch="auto"
                          type="button"
                          variant="secondary"
                          onClick={() => setModalOpen(false)}
                          label={t("cancel")}
                        />
                        <Button
                          size="md"
                          stretch="auto"
                          type="submit"
                          variant="primary"
                          disabled={saving || formState.isSubmitting}
                          loading={saving}
                          label={editingId ? t("update") : t("add")}
                        />
                      </div>
                    </div>
                  </div>
                </DialogBody>
              </DialogMain>
            </form>
          </DialogContent>
        </Dialog>
        <div className="w-full">
          <SettingsHeading
            title={t("workspace_settings.settings.work_item_types.title")}
            description={t("workspace_settings.settings.work_item_types.description")}
            control={
              <Button
                stretch="auto"
                variant="primary"
                size="lg"
                onClick={openCreate}
                label={t("workspace_settings.settings.work_item_types.add_type")}
              />
            }
          />
          {isLoading || !issueTypes ? (
            <div className="flex justify-center py-8">
              <LogoSpinner />
            </div>
          ) : issueTypes.length === 0 ? (
            <p className="py-4 text-13 text-tertiary">{t("no_data_yet")}</p>
          ) : (
            <div className="mt-4 overflow-x-auto rounded-md border border-subtle">
              <table className="w-full min-w-[40rem] text-left text-13">
                <thead className="bg-surface-1 text-tertiary">
                  <tr>
                    <th className="p-2 font-medium">{t("workspace_settings.settings.work_item_types.table.name")}</th>
                    <th className="p-2 font-medium">
                      {t("workspace_settings.settings.work_item_types.table.properties")}
                    </th>
                    <th className="p-2 font-medium">
                      {t("workspace_settings.settings.work_item_types.table.projects")}
                    </th>
                    <th className="p-2 font-medium">{t("workspace_settings.settings.work_item_types.table.status")}</th>
                    <th className="w-40 p-2" />
                  </tr>
                </thead>
                <tbody>
                  {issueTypes.map((row) => (
                    <WorkItemTypeRow
                      key={row.id}
                      row={row}
                      projectNames={(row.project_ids ?? []).map((id) => getProjectById(id)?.name ?? id).join(", ")}
                      onEdit={openEdit}
                      onToggleActive={onToggleActive}
                      onDelete={onDelete}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </SettingsContentWrapper>
    </FormProvider>
  );
}

type TWorkItemTypeRowProps = {
  row: TIssueType;
  projectNames: string;
  onEdit: (row: TIssueType) => void;
  onToggleActive: (row: TIssueType) => void;
  onDelete: (row: TIssueType) => void;
};

function WorkItemTypeRow(props: TWorkItemTypeRowProps) {
  const { row, projectNames, onEdit, onToggleActive, onDelete } = props;
  const { t } = useTranslation();
  const kindBadgeKey = getKindBadgeKey(getIssueTypeKind(row));
  // A system type (approval, review) keeps its switch and its remove button visible but off, with the reason.
  // This is a guard of the page only: the server does not refuse these two requests yet.
  const isSystemManaged = isSystemManagedType(row);
  const systemTypeHint = isSystemManaged ? t("workspace_settings.settings.work_item_types.system_type_hint") : null;

  return (
    <tr className="border-t border-subtle">
      <td className="p-2">
        <div className="flex items-center gap-2 font-medium text-primary">
          <SwitcherIcon logo_props={row.logo_props} LabelIcon={Layers} size={14} />
          <span>{row.name}</span>
          {kindBadgeKey ? (
            <span className="rounded bg-surface-2 px-1.5 py-0.5 text-10 text-tertiary">{t(kindBadgeKey)}</span>
          ) : null}
        </div>
      </td>
      <td className="p-2 text-secondary">{row.properties?.length ?? 0}</td>
      <td className="p-2 text-secondary">
        {projectNames || t("workspace_settings.settings.work_item_types.table.no_projects")}
      </td>
      <td className="p-2">
        <Tooltip label={systemTypeHint} layout="stacked">
          <span className="inline-flex">
            <Switch
              checked={row.is_active}
              onCheckedChange={() => onToggleActive(row)}
              size="sm"
              disabled={isSystemManaged}
            />
          </span>
        </Tooltip>
      </td>
      <td className="p-2 text-right">
        <div className="flex justify-end gap-1">
          <Button stretch="auto" variant="secondary" size="sm" onClick={() => onEdit(row)} label={t("edit")} />
          <Tooltip label={systemTypeHint} layout="stacked">
            <span className="inline-flex">
              <Button
                stretch="auto"
                variant="danger-outline"
                size="sm"
                onClick={() => onDelete(row)}
                disabled={isSystemManaged}
                label={t("remove")}
              />
            </span>
          </Tooltip>
        </div>
      </td>
    </tr>
  );
}

export default observer(WorkItemTypesPage);
