/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssueRaciEntry, TRaciNotificationPreview } from "@plane/types";
import type { TRaciDepartment } from "@plane/utils";
// services
import { issueRaciService } from "@/services/issue/raci.service";
// local imports
import { RaciChip } from "./raci-chip";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  /** The roles on the work item: the preview is read again whenever they change. */
  entries: TIssueRaciEntry[] | undefined;
  departmentsById: Map<string, TRaciDepartment>;
};

/** A key that changes with the roles, in any order. */
const getEntriesKey = (entries: TIssueRaciEntry[] | undefined) =>
  (entries ?? [])
    .map((entry) => `${entry.group_id}:${entry.role}`)
    .toSorted()
    .join(",");

/**
 * "Who will be notified": for every event of the workspace's notification matrix, the departments of the work item
 * whose role hears about it and how many people that makes. Folded until opened.
 */
export function IssueRaciNotificationPreview(props: Props) {
  const { workspaceSlug, projectId, issueId, entries, departmentsById } = props;
  // translation
  const { t } = useTranslation();
  const { data } = useSWR<TRaciNotificationPreview>(
    entries && entries.length > 0
      ? `ISSUE_RACI_NOTIFICATIONS_${workspaceSlug}_${projectId}_${issueId}_${getEntriesKey(entries)}`
      : null,
    () => issueRaciService.getNotificationPreview(workspaceSlug, projectId, issueId),
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );

  if (!entries || entries.length === 0) return null;

  return (
    <details className="group px-2 pt-1">
      <summary className="cursor-pointer text-12 font-medium text-secondary select-none">
        {t("raci.notifications.preview_title")}
      </summary>
      <ul className="mt-1.5 flex flex-col gap-1.5">
        {(data?.events ?? []).map((entry) => (
          <li key={entry.event} className="flex flex-col gap-0.5">
            <span className="text-12 text-secondary">{t(`raci.notifications.events.${entry.event}`)}</span>
            {entry.departments.length === 0 ? (
              <span className="text-11 text-tertiary">{t("raci.notifications.nobody_by_role")}</span>
            ) : (
              <span className="flex flex-wrap items-center gap-1">
                {entry.departments.map((department) => {
                  const known = departmentsById.get(department.group_id);
                  return known ? (
                    <RaciChip key={department.group_id} department={known} role={department.role} />
                  ) : null;
                })}
                <span
                  className={entry.member_ids.length === 0 ? "text-11 text-danger-primary" : "text-11 text-tertiary"}
                >
                  {t("raci.notifications.people", { count: entry.member_ids.length })}
                </span>
              </span>
            )}
          </li>
        ))}
      </ul>
      <p className="mt-1.5 text-11 text-tertiary">{t("raci.notifications.preview_hint")}</p>
    </details>
  );
}
