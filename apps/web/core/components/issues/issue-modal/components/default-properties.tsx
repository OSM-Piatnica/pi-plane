/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import type { Control, UseFormGetValues, UseFormSetValue } from "react-hook-form";
import { Controller } from "react-hook-form";
import { ETabIndices, EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { ParentPropertyIcon } from "@plane/propel/icons";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
// types
import type { ISearchIssueResponse, TIssue } from "@plane/types";
// ui
import { CustomMenu } from "@plane/ui";
import type { TPairedDateNotice, TWorkItemPlanningDates } from "@plane/utils";
import { getTabIndex, planWorkItemDateChange, renderFormattedDate, renderFormattedPayloadDate } from "@plane/utils";
// components
import { CycleDropdown } from "@/components/dropdowns/cycle";
import { DateDropdown } from "@/components/dropdowns/date";
import { DurationDropdown } from "@/components/dropdowns/duration";
import { EstimateDropdown } from "@/components/dropdowns/estimate";
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
import { ModuleDropdown } from "@/components/dropdowns/module/dropdown";
import { PriorityDropdown } from "@/components/dropdowns/priority";
import { StateDropdown } from "@/components/dropdowns/state/dropdown";
import { ParentIssuesListModal } from "@/components/issues/parent-issues-list-modal";
import { IssueLabelSelect } from "@/components/issues/select";
// helpers
// hooks
import { useProjectEstimates } from "@/hooks/store/estimates";
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { usePlatformOS } from "@/hooks/use-platform-os";
// plane web components
import { IssueIdentifier } from "@/plane-web/components/issues/issue-details/issue-identifier";

type TIssueDefaultPropertiesProps = {
  control: Control<TIssue>;
  id: string | undefined;
  projectId: string | null;
  workspaceSlug: string;
  selectedParentIssue: ISearchIssueResponse | null;
  getValues: UseFormGetValues<TIssue>;
  setValue: UseFormSetValue<TIssue>;
  parentId: string | null;
  isDraft: boolean;
  handleFormChange: () => void;
  setSelectedParentIssue: (issue: ISearchIssueResponse) => void;
};

export const IssueDefaultProperties = observer(function IssueDefaultProperties(props: TIssueDefaultPropertiesProps) {
  const {
    control,
    id,
    projectId,
    workspaceSlug,
    selectedParentIssue,
    getValues,
    setValue,
    parentId,
    isDraft,
    handleFormChange,
    setSelectedParentIssue,
  } = props;
  // states
  const [parentIssueListModalOpen, setParentIssueListModalOpen] = useState(false);
  const [pairingConsumed, setPairingConsumed] = useState(false);
  const [dateNotice, setDateNotice] = useState<TPairedDateNotice | null>(null);
  // store hooks
  const { t } = useTranslation();
  const { areEstimateEnabledByProjectId } = useProjectEstimates();
  const { getProjectById } = useProject();
  const { isMobile } = usePlatformOS();
  const { allowPermissions } = useUserPermissions();
  // derived values
  const projectDetails = getProjectById(projectId);

  const { getIndex } = getTabIndex(ETabIndices.ISSUE_FORM, isMobile);

  const canCreateLabel =
    projectId && allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId);

  // Writing the derived fields with setValue rather than the field's own onChange keeps them in
  // dirtyFields, which is what getChangedIssuefields uses to build the update payload.
  //
  // The first manual finish/due entry shows both values before saving. The copy is only a preview:
  // the form names the copied date (`paired_date_defaulted`) and the server verifies eligibility and
  // records the provenance. "Set only ..." removes the copy; once used, it is not offered again.
  const applyDateChange = (change: Partial<TWorkItemPlanningDates>) => {
    const current = getValues();
    const { patch, notice, error } = planWorkItemDateChange(
      { ...current, dates_initialized: current.dates_initialized || pairingConsumed },
      change,
      true
    );
    if (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.error.label"),
        message: t("issue.dates.finish_before_start"),
      });
      return;
    }
    (["start_date", "finish_date", "target_date", "duration"] as const).forEach((key) => {
      if (key in patch) setValue(key, patch[key] as never, { shouldDirty: true });
    });
    if ("finish_date" in change || "target_date" in change) setPairingConsumed(true);
    const copied =
      notice?.code === "due_date_defaulted"
        ? "target_date"
        : notice?.code === "finish_date_defaulted"
          ? "finish_date"
          : undefined;
    // Editing the copied date yourself turns it into a deliberate value.
    const stillCopied =
      copied ??
      (current.paired_date_defaulted && !(current.paired_date_defaulted in change)
        ? current.paired_date_defaulted
        : undefined);
    setValue("paired_date_defaulted", stillCopied, { shouldDirty: true });
    setDateNotice(notice && notice.code !== "finish_date_not_defaulted" ? notice : null);
    handleFormChange();
  };

  const removeCopiedDate = () => {
    const copied = getValues().paired_date_defaulted;
    if (!copied) return;
    setValue(copied, null, { shouldDirty: true });
    setValue("paired_date_defaulted", undefined, { shouldDirty: true });
    setDateNotice(null);
    handleFormChange();
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Controller
        control={control}
        name="state_id"
        render={({ field: { value, onChange } }) => (
          <div className="h-7">
            <StateDropdown
              value={value}
              onChange={(stateId) => {
                onChange(stateId);
                handleFormChange();
              }}
              projectId={projectId ?? undefined}
              buttonVariant="border-with-text"
              tabIndex={getIndex("state_id")}
              isForWorkItemCreation={!id}
            />
          </div>
        )}
      />
      <Controller
        control={control}
        name="priority"
        render={({ field: { value, onChange } }) => (
          <div className="h-7">
            <PriorityDropdown
              value={value}
              onChange={(priority) => {
                onChange(priority);
                handleFormChange();
              }}
              buttonVariant="border-with-text"
              tabIndex={getIndex("priority")}
            />
          </div>
        )}
      />
      <Controller
        control={control}
        name="assignee_ids"
        render={({ field: { value, onChange } }) => (
          <div className="h-7">
            <MemberDropdown
              projectId={projectId ?? undefined}
              value={value}
              onChange={(assigneeIds) => {
                onChange(assigneeIds);
                handleFormChange();
              }}
              buttonVariant={value?.length > 0 ? "transparent-without-text" : "border-with-text"}
              buttonClassName={value?.length > 0 ? "hover:bg-transparent" : ""}
              placeholder={t("assignees")}
              multiple
              tabIndex={getIndex("assignee_ids")}
            />
          </div>
        )}
      />
      <Controller
        control={control}
        name="label_ids"
        render={({ field: { value, onChange } }) => (
          <div className="h-7">
            <IssueLabelSelect
              value={value}
              onChange={(labelIds) => {
                onChange(labelIds);
                handleFormChange();
              }}
              projectId={projectId ?? undefined}
              tabIndex={getIndex("label_ids")}
              createLabelEnabled={!!canCreateLabel}
            />
          </div>
        )}
      />
      <Controller
        control={control}
        name="start_date"
        render={({ field: { value } }) => (
          <div className="h-7">
            <DateDropdown
              value={value}
              onChange={(date) =>
                applyDateChange({ start_date: date ? (renderFormattedPayloadDate(date) ?? null) : null })
              }
              buttonVariant="border-with-text"
              placeholder={t("start_date")}
              tabIndex={getIndex("start_date")}
            />
          </div>
        )}
      />
      <Controller
        control={control}
        name="finish_date"
        render={({ field: { value } }) => (
          <div className="h-7" title={t("issue.dates.help.finish")}>
            <DateDropdown
              value={value}
              onChange={(date) =>
                applyDateChange({ finish_date: date ? (renderFormattedPayloadDate(date) ?? null) : null })
              }
              minDate={getValues().start_date ? new Date(`${getValues().start_date}T00:00:00`) : undefined}
              buttonVariant="border-with-text"
              placeholder={t("common.order_by.finish_date")}
              tabIndex={getIndex("finish_date")}
            />
          </div>
        )}
      />
      <Controller
        control={control}
        name="target_date"
        render={({ field: { value } }) => (
          <div className="h-7" title={t("issue.dates.help.due")}>
            <DateDropdown
              value={value}
              onChange={(date) =>
                applyDateChange({ target_date: date ? (renderFormattedPayloadDate(date) ?? null) : null })
              }
              buttonVariant="border-with-text"
              placeholder={t("due_date")}
              tabIndex={getIndex("target_date")}
            />
          </div>
        )}
      />
      {dateNotice && (
        <div className="flex w-full items-center gap-2 text-body-xs-regular text-tertiary">
          <span>
            {t(
              dateNotice.code === "due_date_defaulted"
                ? "issue.dates.notice.due_defaulted"
                : "issue.dates.notice.finish_defaulted",
              { date: renderFormattedDate(dateNotice.date) ?? dateNotice.date }
            )}
          </span>
          <button type="button" className="font-medium text-primary hover:text-secondary" onClick={removeCopiedDate}>
            {t(dateNotice.code === "due_date_defaulted" ? "issue.dates.only_finish" : "issue.dates.only_due")}
          </button>
        </div>
      )}
      <Controller
        control={control}
        name="duration"
        render={({ field: { value } }) => (
          <div className="h-7">
            <DurationDropdown
              value={value}
              onChange={(duration) => applyDateChange({ duration })}
              buttonVariant="border-with-text"
              placeholder={t("duration")}
              tabIndex={getIndex("duration")}
            />
          </div>
        )}
      />
      {projectDetails?.cycle_view && (
        <Controller
          control={control}
          name="cycle_id"
          render={({ field: { value, onChange } }) => (
            <div className="h-7">
              <CycleDropdown
                projectId={projectId ?? undefined}
                onChange={(cycleId) => {
                  onChange(cycleId);
                  handleFormChange();
                }}
                placeholder={t("cycle.label", { count: 1 })}
                value={value}
                buttonVariant="border-with-text"
                tabIndex={getIndex("cycle_id")}
              />
            </div>
          )}
        />
      )}
      {projectDetails?.module_view && workspaceSlug && (
        <Controller
          control={control}
          name="module_ids"
          render={({ field: { value, onChange } }) => (
            <div className="h-7">
              <ModuleDropdown
                projectId={projectId ?? undefined}
                value={value ?? []}
                onChange={(moduleIds) => {
                  onChange(moduleIds);
                  handleFormChange();
                }}
                placeholder={t("modules")}
                buttonVariant="border-with-text"
                tabIndex={getIndex("module_ids")}
                multiple
                showCount
              />
            </div>
          )}
        />
      )}
      {projectId && areEstimateEnabledByProjectId(projectId) && (
        <Controller
          control={control}
          name="estimate_point"
          render={({ field: { value, onChange } }) => (
            <div className="h-7">
              <EstimateDropdown
                value={value || undefined}
                onChange={(estimatePoint) => {
                  onChange(estimatePoint);
                  handleFormChange();
                }}
                projectId={projectId}
                buttonVariant="border-with-text"
                tabIndex={getIndex("estimate_point")}
                placeholder={t("estimate")}
              />
            </div>
          )}
        />
      )}
      <div className="h-7">
        {parentId ? (
          <CustomMenu
            customButton={
              <button
                type="button"
                className="flex h-full cursor-pointer items-center justify-between gap-1 rounded-sm border-[0.5px] border-strong px-2 py-0.5 text-caption-sm-regular hover:bg-layer-1"
              >
                {selectedParentIssue?.project_id && (
                  <IssueIdentifier
                    projectId={selectedParentIssue.project_id}
                    issueTypeId={selectedParentIssue.type_id}
                    projectIdentifier={selectedParentIssue?.project__identifier}
                    issueSequenceId={selectedParentIssue.sequence_id}
                    size="xs"
                  />
                )}
              </button>
            }
            placement="bottom-start"
            className="h-full w-full"
            customButtonClassName="h-full"
            tabIndex={getIndex("parent_id")}
          >
            <>
              <CustomMenu.MenuItem className="!p-1" onClick={() => setParentIssueListModalOpen(true)}>
                {t("change_parent_issue")}
              </CustomMenu.MenuItem>
              <Controller
                control={control}
                name="parent_id"
                render={({ field: { onChange } }) => (
                  <CustomMenu.MenuItem
                    className="!p-1"
                    onClick={() => {
                      onChange(null);
                      handleFormChange();
                    }}
                  >
                    {t("remove_parent_issue")}
                  </CustomMenu.MenuItem>
                )}
              />
            </>
          </CustomMenu>
        ) : (
          <button
            type="button"
            className="flex h-full cursor-pointer items-center justify-between gap-1 rounded-sm border-[0.5px] border-strong px-2 py-0.5 text-caption-sm-regular hover:bg-layer-1"
            onClick={() => setParentIssueListModalOpen(true)}
          >
            <ParentPropertyIcon className="h-3 w-3 flex-shrink-0" />
            <span className="whitespace-nowrap">{t("add_parent")}</span>
          </button>
        )}
      </div>
      <Controller
        control={control}
        name="parent_id"
        render={({ field: { onChange } }) => (
          <ParentIssuesListModal
            isOpen={parentIssueListModalOpen}
            handleClose={() => setParentIssueListModalOpen(false)}
            onChange={(issue) => {
              onChange(issue.id);
              handleFormChange();
              setSelectedParentIssue(issue);
            }}
            projectId={projectId ?? undefined}
            issueId={isDraft ? undefined : id}
          />
        )}
      />
    </div>
  );
});
