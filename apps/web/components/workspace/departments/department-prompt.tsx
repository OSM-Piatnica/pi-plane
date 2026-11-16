/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
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
import { setToast } from "@plane/blocks/toast";
// helpers
import { getDepartmentsKey, shouldAskForDepartment } from "@/helpers/department";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// services
import { userGroupService } from "@/services/user-group.service";
// local imports
import { DepartmentSelect } from "./department-select";

type Props = {
  workspaceSlug: string | undefined;
};

const postponedKey = (workspaceSlug: string) => `department-prompt-postponed-${workspaceSlug}`;

const readPostponed = (workspaceSlug: string): boolean => {
  try {
    return window.sessionStorage.getItem(postponedKey(workspaceSlug)) === "1";
  } catch {
    return false;
  }
};

const writePostponed = (workspaceSlug: string) => {
  try {
    window.sessionStorage.setItem(postponedKey(workspaceSlug), "1");
  } catch {
    // without session storage the question simply comes back on the next page load
  }
};

/**
 * Asks a member of the workspace for their department when the workspace has departments and they have none.
 * It can be put off ("Later") until the next browser session, so it never stands in the way of work.
 */
export const DepartmentPrompt = observer(function DepartmentPrompt(props: Props) {
  const { workspaceSlug } = props;
  // store hooks
  const { workspaceUserInfo, setWorkspaceUserDepartment } = useUserPermissions();
  // derived values
  const membership = workspaceSlug ? workspaceUserInfo[workspaceSlug] : undefined;
  const needsDepartment = Boolean(membership) && !membership?.department;

  // The list is only read for people who have no department yet
  const { data: departments } = useSWR(
    workspaceSlug && needsDepartment ? getDepartmentsKey(workspaceSlug) : null,
    workspaceSlug ? () => userGroupService.listDepartments(workspaceSlug) : null,
    { revalidateOnFocus: false }
  );

  if (!workspaceSlug || !membership) return null;
  // Departments the identity provider manages are given by it, and cannot be chosen
  const choosable = departments?.filter((department) => !department.is_external);

  return (
    <DepartmentPromptDialog
      key={workspaceSlug}
      workspaceSlug={workspaceSlug}
      workspaceMemberId={membership.id}
      currentDepartment={membership.department}
      departments={choosable}
      onSaved={(departmentId) => setWorkspaceUserDepartment(workspaceSlug, departmentId)}
    />
  );
});

type DialogProps = {
  workspaceSlug: string;
  workspaceMemberId: string;
  currentDepartment: string | null | undefined;
  departments: Awaited<ReturnType<typeof userGroupService.listDepartments>> | undefined;
  onSaved: (departmentId: string) => void;
};

function DepartmentPromptDialog(props: DialogProps) {
  const { workspaceSlug, workspaceMemberId, currentDepartment, departments, onSaved } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [isPostponed, setIsPostponed] = useState(() => readPostponed(workspaceSlug));
  const [selected, setSelected] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isOpen = shouldAskForDepartment({
    departments,
    currentDepartment,
    isMembershipLoaded: true,
    isPostponed,
  });
  if (!isOpen || !departments) return null;

  const handlePostpone = () => {
    writePostponed(workspaceSlug);
    setIsPostponed(true);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    setIsSubmitting(true);
    try {
      await userGroupService.setMemberDepartment(workspaceSlug, workspaceMemberId, selected);
      onSaved(selected);
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("workspace_settings.settings.departments.updated"),
      });
    } catch (error) {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: (error as { error?: string })?.error ?? t("something_went_wrong_please_try_again"),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) handlePostpone();
      }}
    >
      <DialogContent size="md">
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>{t("workspace_settings.settings.departments.prompt_title")}</DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-3">
                <p className="text-13 text-secondary">
                  {t("workspace_settings.settings.departments.prompt_description")}
                </p>
                <DepartmentSelect
                  departments={departments}
                  value={selected}
                  onChange={setSelected}
                  variant="select-xl"
                  className="w-full"
                />
              </div>
            </DialogBody>
            <DialogActions>
              <Button
                size="md"
                stretch="auto"
                type="button"
                variant="secondary"
                onClick={handlePostpone}
                label={t("workspace_settings.settings.departments.later")}
              />
              <Button
                size="md"
                stretch="auto"
                type="submit"
                variant="primary"
                loading={isSubmitting}
                disabled={!selected}
                label={t("save")}
              />
            </DialogActions>
          </DialogMain>
        </form>
      </DialogContent>
    </Dialog>
  );
}
