/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { setPromiseToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// components
import { ProjectCreateIssueTypesAssign } from "@/components/projects/create/issue-types-assign";
// helpers
import { getBulkAssignDefaultTypeId } from "@/helpers/issue-type-options";
// hooks
import { useProjectIssueTypes } from "@/hooks/use-project-issue-types";
// services
import { IssueTypeService } from "@/services/issue-type.service";

const issueTypeService = new IssueTypeService();

type Props = {
  projectId: string;
  workspaceSlug: string;
};

/**
 * Which workspace work item types the project can use. A change is saved right away.
 * Epic types are not listed: the Epics switch owns them, and the bulk endpoint never unlinks them.
 * System-managed types (approval, review) are not listed either: the bulk endpoint never links or unlinks them.
 */
export const ProjectSettingsIssueTypesControl = observer(function ProjectSettingsIssueTypesControl(props: Props) {
  const { projectId, workspaceSlug } = props;
  // states
  const [isSaving, setIsSaving] = useState(false);
  // hooks
  const { t } = useTranslation();
  const { types, mutate } = useProjectIssueTypes(workspaceSlug, projectId);
  // derived values
  const selectedIds = types.map((row) => row.issue_type_id);
  const currentDefaultId = types.find((row) => row.is_default)?.issue_type_id;

  const handleChange = (ids: string[]) => {
    setIsSaving(true);
    const defaultTypeId = getBulkAssignDefaultTypeId(ids, types, currentDefaultId);
    const savePromise = issueTypeService
      .bulkAssignProjectTypes(workspaceSlug, projectId, { issue_type_ids: ids, default_type_id: defaultTypeId })
      .then(() => mutate())
      .finally(() => setIsSaving(false));

    setPromiseToast(savePromise, {
      loading: t("project_components.features.updating"),
      success: {
        title: t("toast.success"),
        message: () => t("project_components.features.updated"),
      },
      error: {
        title: t("toast.error"),
        message: () => t("project_components.features.update_error"),
      },
    });
  };

  return (
    <div className="rounded-lg border border-subtle bg-layer-2 px-4 py-3">
      <p className="pb-2 text-body-sm-medium text-primary">
        {t("project_create.features.work_item_types.assign_label")}
      </p>
      <ProjectCreateIssueTypesAssign
        workspaceSlug={workspaceSlug}
        value={selectedIds}
        onChange={handleChange}
        disabled={isSaving}
        hideEpics
      />
    </div>
  );
});
