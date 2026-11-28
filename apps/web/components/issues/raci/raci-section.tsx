/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { MembersOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { RACI_ROLES } from "@plane/types";
import type { TIssueRaci, TRaciRole } from "@plane/types";
import { getRaciEditorDepartments, getRaciRole, setRaciRole } from "@plane/utils";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
// hooks
import { useDepartments } from "@/hooks/use-departments";
import { useProject } from "@/hooks/store/use-project";
import { useWorkspaceFeatures } from "@/hooks/use-workspace-features";
// lib
import { store } from "@/lib/store-context";
// services
import { issueRaciService } from "@/services/issue/raci.service";
// local imports
import { RaciChip } from "./raci-chip";
import { IssueRaciNotificationPreview } from "./raci-notification-preview";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

const NONE = "";

/**
 * The RACI of a work item: every active department with a picker of none and the four roles. Read-only for
 * people who may not change it (the API says so), and not there at all while the project has RACI off.
 */
export const IssueRaciSection = observer(function IssueRaciSection(props: Props) {
  const { workspaceSlug, projectId, issueId } = props;
  // translation
  const { t } = useTranslation();
  // store hooks
  const { getProjectById } = useProject();
  const { isFeatureEnabled } = useWorkspaceFeatures();
  // derived values: RACI is on for the workspace and for the project
  const isEnabled = isFeatureEnabled("raci") && Boolean(getProjectById(projectId)?.is_raci_enabled);
  const key = `ISSUE_RACI_${workspaceSlug}_${projectId}_${issueId}`;
  const { data, mutate } = useSWR<TIssueRaci>(
    isEnabled ? key : null,
    () => issueRaciService.getRaci(workspaceSlug, projectId, issueId),
    { revalidateOnFocus: false }
  );
  const { departments, departmentsById } = useDepartments(workspaceSlug, isEnabled);

  if (!isEnabled) return null;

  const entries = data?.raci;
  const canEdit = data?.can_edit ?? false;
  const listed = getRaciEditorDepartments(departments, entries);

  const handleChange = async (departmentId: string, role: TRaciRole | null) => {
    if (!data) return;
    const next = setRaciRole(entries, departmentId, role);
    try {
      await mutate(
        async () => {
          const saved = await issueRaciService.setRaci(workspaceSlug, projectId, issueId, next);
          store.issue.issues.updateIssue(issueId, { raci: saved.raci });
          return saved;
        },
        { optimisticData: { ...data, raci: next }, rollbackOnError: true, revalidate: false }
      );
    } catch (error) {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: (error as { error?: string } | undefined)?.error ?? t("raci.save_failed"),
      });
    }
  };

  return (
    <SidebarPropertyListItem icon={MembersOutline} label={t("raci.title")} childrenClassName="flex-col items-stretch">
      {listed.length === 0 && <span className="px-2 text-13 text-tertiary">{t("raci.no_departments")}</span>}
      {listed.map((department) => {
        const role = getRaciRole(entries, department.id);
        return (
          <div key={department.id} className="flex items-center justify-between gap-2 px-2">
            <RaciChip department={department} role={role} />
            <select
              aria-label={t("raci.role_of", { department: department.name })}
              value={role ?? NONE}
              disabled={!canEdit}
              onChange={(event) => void handleChange(department.id, (event.target.value || null) as TRaciRole | null)}
              className="h-6 rounded-md border border-subtle bg-surface-1 px-1.5 text-12 text-secondary disabled:opacity-60"
            >
              <option value={NONE}>{t("raci.none")}</option>
              {RACI_ROLES.map((option) => (
                <option key={option} value={option}>
                  {t(`raci.roles.${option}.letter`)} · {t(`raci.roles.${option}.name`)}
                </option>
              ))}
            </select>
          </div>
        );
      })}
      <IssueRaciNotificationPreview
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        issueId={issueId}
        entries={entries}
        departmentsById={departmentsById}
      />
    </SidebarPropertyListItem>
  );
});
