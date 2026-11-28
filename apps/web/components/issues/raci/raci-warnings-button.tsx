/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { RACI_ITEM_WARNINGS } from "@plane/types";
import type { TRaciProjectWarnings } from "@plane/types";
import { countRaciWarnings, generateWorkItemLink } from "@plane/utils";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { useDepartments } from "@/hooks/use-departments";
import { useWorkspaceFeatures } from "@/hooks/use-workspace-features";
// services
import { issueRaciService } from "@/services/issue/raci.service";
// local imports
import { RaciChip } from "./raci-chip";

type Props = {
  workspaceSlug: string;
  projectId: string;
};

/**
 * The RACI warnings of a project behind a button that shows how many there are: work items without a responsible
 * department, milestones without an approver, departments nobody would hear for, and gaps in the dependencies.
 * Nothing while RACI is off, for guests, or while there is nothing to warn about.
 */
export const RaciWarningsButton = observer(function RaciWarningsButton(props: Props) {
  const { workspaceSlug, projectId } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [isOpen, setIsOpen] = useState(false);
  // store hooks
  const { getProjectById } = useProject();
  const { isFeatureEnabled } = useWorkspaceFeatures();
  const { allowPermissions } = useUserPermissions();
  // derived values
  const project = getProjectById(projectId);
  const isEnabled =
    isFeatureEnabled("raci") &&
    Boolean(project?.is_raci_enabled) &&
    allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.PROJECT);
  const { data, mutate } = useSWR<TRaciProjectWarnings>(
    isEnabled ? `PROJECT_RACI_WARNINGS_${workspaceSlug}_${projectId}` : null,
    () => issueRaciService.getProjectWarnings(workspaceSlug, projectId),
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  const { departmentsById } = useDepartments(workspaceSlug, isEnabled && isOpen);

  const total = countRaciWarnings(data?.counts);
  if (!isEnabled || !data || total === 0) return null;

  const open = () => {
    setIsOpen(true);
    void mutate();
  };

  return (
    <>
      <Button
        size="md"
        stretch="auto"
        variant="secondary"
        onClick={open}
        label={t("raci.warnings.button", { count: total })}
      />
      {isOpen && (
        <Dialog open onOpenChange={(next) => !next && setIsOpen(false)}>
          <DialogContent size="lg">
            <DialogMain>
              <DialogHeader>
                <DialogHeading>
                  <DialogTitle>{t("raci.warnings.title")}</DialogTitle>
                </DialogHeading>
              </DialogHeader>
              <DialogBody>
                <div className="flex flex-col gap-4">
                  <p className="text-13 text-secondary">{t("raci.warnings.description")}</p>
                  {RACI_ITEM_WARNINGS.map((kind) =>
                    data.counts[kind] > 0 ? (
                      <section key={kind} className="flex flex-col gap-1">
                        <h5 className="text-13 font-medium text-primary">
                          {t(`raci.warnings.kinds.${kind}`)} ({data.counts[kind]})
                        </h5>
                        <ul className="flex flex-col gap-0.5">
                          {data.items[kind].map((item) => (
                            <li key={item.id} className="truncate text-13">
                              <Link
                                href={generateWorkItemLink({
                                  workspaceSlug,
                                  projectId,
                                  issueId: item.id,
                                  projectIdentifier: project?.identifier,
                                  sequenceId: item.sequence_id,
                                })}
                                className="text-secondary hover:text-primary hover:underline"
                              >
                                <span className="text-tertiary">
                                  {project?.identifier}-{item.sequence_id}
                                </span>{" "}
                                {item.name}
                              </Link>
                            </li>
                          ))}
                        </ul>
                        {data.counts[kind] > data.items[kind].length && (
                          <p className="text-11 text-tertiary">
                            {t("raci.warnings.more", { count: data.counts[kind] - data.items[kind].length })}
                          </p>
                        )}
                      </section>
                    ) : null
                  )}
                  {data.departments.length > 0 && (
                    <section className="flex flex-col gap-1">
                      <h5 className="text-13 font-medium text-primary">
                        {t("raci.warnings.kinds.department_without_members")} ({data.departments.length})
                      </h5>
                      <ul className="flex flex-col gap-1">
                        {data.departments.map((entry) => {
                          const department = departmentsById.get(entry.group_id);
                          return (
                            <li key={entry.group_id} className="flex items-center gap-2 text-13 text-secondary">
                              {department && <RaciChip department={department} />}
                              <span>{t(`raci.warnings.reasons.${entry.reason}`)}</span>
                            </li>
                          );
                        })}
                      </ul>
                    </section>
                  )}
                </div>
              </DialogBody>
              <DialogActions>
                <Button
                  size="md"
                  stretch="auto"
                  type="button"
                  variant="secondary"
                  onClick={() => setIsOpen(false)}
                  label={t("close")}
                />
              </DialogActions>
            </DialogMain>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
});
