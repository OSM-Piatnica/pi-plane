/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useController, type Control, type Path } from "react-hook-form";
import { observer } from "mobx-react";
import { Layers } from "lucide-react";
import type { EditorRefApi } from "@plane/editor";
import { Select } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import type { TBulkIssueProperties, TIssue, TProjectIssueType } from "@plane/types";
import { SwitcherIcon } from "@/components/common/switcher-label";
import { IssueTypeLockedLabel } from "@/components/issues/issue-details/issue-type-locked-label";
import { getLockedProjectIssueType, getSelectableProjectIssueTypes } from "@/helpers/issue-type-options";
import { useProject } from "@/hooks/store/use-project";
import { useProjectIssueTypes } from "@/hooks/use-project-issue-types";

export type TIssueFields = TIssue & TBulkIssueProperties;

export type TIssueTypeDropdownVariant = "xs" | "sm";

export type TIssueTypeSelectProps<T extends Partial<TIssueFields>> = {
  control: Control<T>;
  projectId: string | null;
  editorRef?: React.MutableRefObject<EditorRefApi | null>;
  disabled?: boolean;
  variant?: TIssueTypeDropdownVariant;
  placeholder?: string;
  isRequired?: boolean;
  renderChevron?: boolean;
  dropDownContainerClassName?: string;
  showMandatoryFieldInfo?: boolean;
  handleFormChange?: () => void;
  /** Offer the system-managed kinds (approval, review) too. Off: a person does not pick those by hand. */
  includeSystemManaged?: boolean;
};

type TIssueTypeOptionsProps = {
  options: TProjectIssueType[];
  value: string | null;
  onChange: (value: string | null) => void;
  disabled: boolean;
  /** Shown while nothing is selected */
  label: string;
  renderChevron: boolean;
};

/** The types a person may pick, as a select; nothing when there are none. */
function IssueTypeOptions(props: TIssueTypeOptionsProps) {
  const { options, value, onChange, disabled, label, renderChevron } = props;
  if (options.length === 0) return null;
  const selectedOption = options.find((row) => row.issue_type_id === value) ?? null;
  const selected = selectedOption?.issue_type_detail;

  return (
    <div className="min-w-0 sm:max-w-[12rem]">
      <Select<TProjectIssueType>
        getValues={() => options}
        value={selectedOption}
        onChange={(row) => onChange(row || null)}
        disabled={disabled}
        getOptionValue={(row) => row.issue_type_id}
        getOptionLabel={(row) => row.issue_type_detail?.name ?? ""}
        getOptionIcon={(row) => (
          <SwitcherIcon logo_props={row.issue_type_detail?.logo_props} LabelIcon={Layers} size={12} />
        )}
        showSearch={false}
        pinSelected={false}
      >
        <Select.Trigger
          variant="select-md"
          className="w-full max-w-full truncate"
          appendIcon={renderChevron ? undefined : null}
          tabIndex={0}
        >
          {selected ? (
            <span className="flex items-center gap-1.5 truncate">
              <SwitcherIcon logo_props={selected.logo_props} LabelIcon={Layers} size={12} />
              <span className="truncate">{selected.name}</span>
            </span>
          ) : (
            label
          )}
        </Select.Trigger>
      </Select>
    </div>
  );
}

export const IssueTypeSelect = observer(function IssueTypeSelect<T extends Partial<TIssueFields>>(
  props: TIssueTypeSelectProps<T>
) {
  const {
    control,
    projectId,
    disabled = false,
    renderChevron = false,
    placeholder,
    handleFormChange,
    includeSystemManaged = false,
  } = props;
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const { getProjectById } = useProject();
  const slug = workspaceSlug?.toString();
  const project = projectId ? getProjectById(projectId) : undefined;
  const issueTypesEnabled = Boolean(project?.is_issue_type_enabled);

  const { field } = useController({
    control,
    name: "type_id" as Path<T>,
  });

  const { types, defaultTypeId, isLoading } = useProjectIssueTypes(slug, issueTypesEnabled ? projectId : null);

  useEffect(() => {
    if (!issueTypesEnabled || !projectId || field.value || !defaultTypeId) return;
    field.onChange(defaultTypeId);
  }, [issueTypesEnabled, projectId, field.value, defaultTypeId, field]);

  if (!projectId || !slug || !issueTypesEnabled || types.length === 0) {
    return null;
  }

  // A work item that already has a system-managed type shows it read-only: the server refuses the switch
  const lockedType = includeSystemManaged ? undefined : getLockedProjectIssueType(types, field.value as string | null);
  if (lockedType?.issue_type_detail) {
    return (
      <div className="min-w-0 sm:max-w-[12rem]">
        <IssueTypeLockedLabel issueType={lockedType.issue_type_detail} />
      </div>
    );
  }

  return (
    <IssueTypeOptions
      options={getSelectableProjectIssueTypes(types, { includeSystemManaged })}
      value={field.value as string | null}
      onChange={(value) => {
        field.onChange(value);
        handleFormChange?.();
      }}
      disabled={disabled || isLoading}
      label={isLoading ? t("work_item_types.loading") : (placeholder ?? t("work_item_types.select_placeholder"))}
      renderChevron={renderChevron}
    />
  );
});
