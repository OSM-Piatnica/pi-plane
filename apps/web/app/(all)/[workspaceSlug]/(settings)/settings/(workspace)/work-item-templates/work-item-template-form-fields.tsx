/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Controller, type Control, useWatch } from "react-hook-form";
import { Field } from "@makeplane/propel/components/field";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import { CalendarOutline } from "@makeplane/propel/icons";
import { DateSelect } from "@/components/dropdowns/date-select";
import { ETabIndices } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
import { getDate, renderFormattedPayloadDate, getTabIndex } from "@plane/utils";
import { CycleSelect } from "@/components/dropdowns/cycle/cycle-select";
import { EstimateSelect } from "@/components/dropdowns/estimate/estimate-select";
import { LabelSelect } from "@/components/dropdowns/label/label-select";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { ModuleSelect } from "@/components/dropdowns/module/module-select";
import { PrioritySelect } from "@/components/dropdowns/priority/priority-select";
import { StateSelect } from "@/components/dropdowns/state/state-select";
import { useProjectEstimates } from "@/hooks/store/estimates";
import { useProject } from "@/hooks/store/use-project";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { IssueTypeSelect } from "@/components/issues/issue-modal";
import type { TWorkItemTemplateFormFields } from "./work-item-template-form.types";

export type { TWorkItemTemplateFormFields } from "./work-item-template-form.types";

type TDefaultWorkItemFieldsProps = {
  control: Control<TWorkItemTemplateFormFields>;
  projectId: string | null;
  workspaceSlug: string;
};

export const WorkItemTemplateDefaultValueFields = observer(function WorkItemTemplateDefaultValueFields(
  props: TDefaultWorkItemFieldsProps
) {
  const { control, projectId, workspaceSlug } = props;
  const { t } = useTranslation();
  const { areEstimateEnabledByProjectId } = useProjectEstimates();
  const { getProjectById } = useProject();
  const { isMobile } = usePlatformOS();
  const startOfTheWeek = useStartOfTheWeek();

  const startDate = useWatch({ control, name: "start_date" });
  const targetDate = useWatch({ control, name: "target_date" });

  const projectDetails = getProjectById(projectId);
  const { getIndex } = getTabIndex(ETabIndices.ISSUE_FORM, isMobile);

  const issueControl = control as unknown as Control<Partial<TIssue>>;

  const minDate = getDate(startDate);
  minDate?.setDate(minDate.getDate());
  const maxDate = getDate(targetDate);
  maxDate?.setDate(maxDate.getDate());

  return (
    <div className="space-y-3 rounded-md border border-subtle bg-layer-1 p-4">
      <h4 className="text-14 font-medium text-primary">
        {t("workspace_settings.settings.work_item_templates.form.default_values_section_title")}
      </h4>
      <p className="-mt-1 text-11 text-tertiary">
        {t("workspace_settings.settings.work_item_templates.form.default_values_section_hint")}
      </p>

      {!projectId ? (
        <p className="rounded-md border border-subtle bg-layer-2 px-3 py-2 text-12 text-tertiary">
          {t("workspace_settings.settings.work_item_templates.form.project_required_for_scoped_fields")}
        </p>
      ) : null}

      {projectId ? (
        <div className="h-7 max-w-xs">
          <IssueTypeSelect control={issueControl} projectId={projectId} handleFormChange={() => {}} renderChevron />
        </div>
      ) : null}

      <div>
        <label className="text-12 text-tertiary" htmlFor="work-item-payload-name">
          {t("workspace_settings.settings.work_item_templates.form.default_work_item_name")}
        </label>
        <Controller
          name="workItemName"
          control={control}
          render={({ field }) => (
            <div className="mt-1">
              <Field name="workItemName">
                <InputGroup size="lg">
                  <Input
                    size="lg"
                    id="work-item-payload-name"
                    value={field.value}
                    onChange={field.onChange}
                    placeholder={t(
                      "workspace_settings.settings.work_item_templates.form.default_work_item_name_placeholder"
                    )}
                  />
                </InputGroup>
              </Field>
            </div>
          )}
        />
      </div>
      <div>
        <label className="text-12 text-tertiary" htmlFor="work-item-payload-desc">
          {t("workspace_settings.settings.work_item_templates.form.default_work_item_description")}
        </label>
        <p className="pt-0.5 pb-1 text-11 text-tertiary">
          {t("workspace_settings.settings.work_item_templates.form.default_work_item_description_hint")}
        </p>
        <Controller
          name="workItemDescriptionPlain"
          control={control}
          render={({ field }) => (
            <div className="mt-1">
              <Field name="workItemDescriptionPlain">
                <TextAreaGroup resize="vertical">
                  <TextArea
                    size="lg"
                    surface="field"
                    id="work-item-payload-desc"
                    value={field.value}
                    onChange={field.onChange}
                    rows={8}
                    placeholder={t(
                      "workspace_settings.settings.work_item_templates.form.default_work_item_description_placeholder"
                    )}
                  />
                </TextAreaGroup>
              </Field>
            </div>
          )}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {projectId ? (
          <Controller
            control={control}
            name="state_id"
            render={({ field: { value, onChange } }) => (
              <StateSelect
                value={value}
                onChange={(stateId) => onChange(stateId)}
                projectId={projectId ?? undefined}
                variant="pill-md"
                tabIndex={getIndex("state_id")}
                isForWorkItemCreation
              />
            )}
          />
        ) : null}
        <Controller
          control={control}
          name="priority"
          render={({ field: { value, onChange } }) => (
            <PrioritySelect
              value={value}
              onChange={(p) => onChange(p)}
              variant="pill-md"
              placeholder={t("common.priority")}
            />
          )}
        />
        <Controller
          name="assignee_ids"
          control={control}
          render={({ field: { value, onChange } }) => (
            <MemberSelect
              projectId={projectId ?? undefined}
              value={value}
              onChange={(ids) => onChange(ids)}
              variant={value?.length > 0 ? "avatar-group-md" : "pill-md"}
              placeholder={t("assignees")}
              multiple
            />
          )}
        />
        {projectId ? (
          <Controller
            control={control}
            name="label_ids"
            render={({ field: { value, onChange } }) => (
              <LabelSelect
                value={value ?? []}
                onChange={(labelIds) => onChange(labelIds)}
                projectId={projectId ?? undefined}
                variant="pill-md"
                placeholder={t("labels")}
                tabIndex={getIndex("label_ids")}
              />
            )}
          />
        ) : null}
        <Controller
          control={control}
          name="start_date"
          render={({ field: { value, onChange } }) => (
            <DateSelect
              value={getDate(value) ?? null}
              onChange={(date) => onChange(date ? renderFormattedPayloadDate(date) : null)}
              maxDate={maxDate ?? undefined}
              placeholder={t("start_date")}
              icon={<CalendarOutline />}
              weekStartsOn={startOfTheWeek}
              clearable
              tabIndex={getIndex("start_date")}
              variant="pill-md"
            />
          )}
        />
        <Controller
          control={control}
          name="target_date"
          render={({ field: { value, onChange } }) => (
            <DateSelect
              value={getDate(value) ?? null}
              onChange={(date) => onChange(date ? renderFormattedPayloadDate(date) : null)}
              minDate={minDate ?? undefined}
              placeholder={t("due_date")}
              icon={<CalendarOutline />}
              weekStartsOn={startOfTheWeek}
              clearable
              tabIndex={getIndex("target_date")}
              variant="pill-md"
            />
          )}
        />
        {projectId && projectDetails?.cycle_view ? (
          <Controller
            control={control}
            name="cycle_id"
            render={({ field: { value, onChange } }) => (
              <CycleSelect
                projectId={projectId}
                onChange={(cycleId) => onChange(cycleId)}
                placeholder={t("cycle.label", { count: 1 })}
                value={value ?? null}
                variant="pill-md"
                clearable
                tabIndex={getIndex("cycle_id")}
              />
            )}
          />
        ) : null}
        {projectId && projectDetails?.module_view && workspaceSlug ? (
          <Controller
            control={control}
            name="module_ids"
            render={({ field: { value, onChange } }) => (
              <ModuleSelect
                projectId={projectId}
                value={value ?? []}
                onChange={(moduleIds) => onChange(moduleIds)}
                placeholder={t("modules")}
                variant="pill-md"
                tabIndex={getIndex("module_ids")}
                multiple
              />
            )}
          />
        ) : null}
        {projectId && areEstimateEnabledByProjectId(projectId) ? (
          <Controller
            control={control}
            name="estimate_point"
            render={({ field: { value, onChange } }) => (
              <EstimateSelect
                value={value || undefined}
                onChange={(estimatePoint) => onChange(estimatePoint)}
                projectId={projectId}
                variant="pill-md"
                placeholder={t("estimate")}
                tabIndex={getIndex("estimate_point")}
              />
            )}
          />
        ) : null}
      </div>
    </div>
  );
});
