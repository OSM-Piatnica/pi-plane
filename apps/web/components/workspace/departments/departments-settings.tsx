/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import useSWR, { useSWRConfig } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Badge } from "@makeplane/propel/components/badge";
import { Button } from "@makeplane/propel/components/button";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import type { TUserGroup, TUserGroupFormData } from "@plane/types";
// components
import { GroupMembersModal } from "@/components/workspace/user-groups/group-members-modal";
// helpers
import type { TDepartmentImportRow } from "@/helpers/department";
import {
  getAllDepartmentsKey,
  getDepartmentsKey,
  getMovedSortOrder,
  getUserGroupsKey,
  sortDepartments,
} from "@/helpers/department";
// services
import { userGroupService } from "@/services/user-group.service";
// local imports
import { DepartmentColorDot } from "./department-color-dot";
import { DepartmentFormModal } from "./department-form-modal";
import { DepartmentImportModal } from "./department-import-modal";

type Props = {
  workspaceSlug: string;
};

export const DepartmentsSettings = observer(function DepartmentsSettings(props: Props) {
  const { workspaceSlug } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [formState, setFormState] = useState<{ department?: TUserGroup } | null>(null);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [membersOf, setMembersOf] = useState<TUserGroup | null>(null);
  const [toDelete, setToDelete] = useState<TUserGroup | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const { mutate: mutateGlobal } = useSWRConfig();
  const { data: groups, mutate } = useSWR(getUserGroupsKey(workspaceSlug), () => userGroupService.list(workspaceSlug));

  // derived values
  const departments = useMemo(
    () => sortDepartments((groups ?? []).filter((group) => group.kind === "department")),
    [groups]
  );

  /** The groups and the picker lists everywhere else follow what was changed here. */
  const refresh = async () => {
    await mutate();
    await mutateGlobal(getDepartmentsKey(workspaceSlug));
    await mutateGlobal(getAllDepartmentsKey(workspaceSlug));
  };

  const showError = (error: unknown) =>
    setToast({
      type: "error",
      title: t("toast.error"),
      message: (error as { error?: string })?.error ?? t("something_went_wrong_please_try_again"),
    });

  const showSuccess = (message: string) => setToast({ type: "success", title: t("toast.success"), message });

  const handleSubmit = async (data: Partial<TUserGroupFormData>) => {
    try {
      if (formState?.department) {
        await userGroupService.update(workspaceSlug, formState.department.id, data);
      } else {
        await userGroupService.create(workspaceSlug, { ...data, name: data.name ?? "", kind: "department" });
      }
      await refresh();
      showSuccess(
        formState?.department
          ? t("workspace_settings.settings.departments.updated")
          : t("workspace_settings.settings.departments.created")
      );
    } catch (error) {
      showError(error);
      throw error;
    }
  };

  const handleImport = async (rows: TDepartmentImportRow[]) => {
    let created = 0;
    try {
      // One after another, not at once: every department takes the place after the last one, in the order of the list
      await rows.reduce(
        (previous, row) =>
          previous.then(async () => {
            await userGroupService.create(workspaceSlug, { name: row.name, code: row.code, kind: "department" });
            created += 1;
            return undefined;
          }),
        Promise.resolve<void>(undefined)
      );
    } catch (error) {
      showError(error);
      throw error;
    } finally {
      await refresh();
      if (created > 0) showSuccess(t("workspace_settings.settings.departments.import_done", { count: created }));
    }
  };

  const handleUpdate = async (department: TUserGroup, data: Partial<TUserGroupFormData>) => {
    setBusyId(department.id);
    try {
      await userGroupService.update(workspaceSlug, department.id, data);
      await refresh();
    } catch (error) {
      showError(error);
    } finally {
      setBusyId(null);
    }
  };

  const handleMove = (department: TUserGroup, direction: -1 | 1) => {
    const sortOrder = getMovedSortOrder(departments, department.id, direction);
    if (sortOrder === null) return;
    void handleUpdate(department, { sort_order: sortOrder });
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    setIsDeleting(true);
    try {
      await userGroupService.remove(workspaceSlug, toDelete.id);
      await refresh();
      setToDelete(null);
      showSuccess(t("workspace_settings.settings.departments.deleted"));
    } catch (error) {
      showError(error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className="size-full">
      <div className="flex items-start justify-between gap-4 pb-4">
        <div className="flex flex-col gap-1">
          <h4 className="text-h3-medium">{t("workspace_settings.settings.departments.title")}</h4>
          <p className="text-13 text-secondary">{t("workspace_settings.settings.departments.description")}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            size="md"
            stretch="auto"
            variant="secondary"
            onClick={() => setIsImportOpen(true)}
            label={t("workspace_settings.settings.departments.import")}
          />
          <Button
            size="md"
            stretch="auto"
            variant="primary"
            onClick={() => setFormState({})}
            label={t("workspace_settings.settings.departments.add")}
          />
        </div>
      </div>

      {groups && departments.length === 0 && (
        <div className="rounded-lg border border-subtle p-6 text-13 text-secondary">
          {t("workspace_settings.settings.departments.empty")}
        </div>
      )}

      {departments.length > 0 && (
        <ul className="flex flex-col divide-y divide-subtle rounded-lg border border-subtle">
          {departments.map((department, index) => (
            <li key={department.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <DepartmentColorDot color={department.color} />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {department.code && (
                      <span className="rounded-sm bg-layer-1 px-1.5 py-0.5 text-11 font-medium text-secondary">
                        {department.code}
                      </span>
                    )}
                    <span
                      className={`truncate text-14 font-medium ${department.is_active ? "text-primary" : "text-placeholder"}`}
                    >
                      {department.name}
                    </span>
                    {!department.is_active && (
                      <Badge
                        variant="neutral"
                        size="sm"
                        label={t("workspace_settings.settings.departments.inactive")}
                      />
                    )}
                    {department.is_external && (
                      <span className="rounded-full bg-layer-1 px-2 py-0.5 text-11 text-secondary">
                        {t("workspace_settings.settings.groups.managed_by", {
                          provider: t(`workspace_settings.settings.groups.sources.${department.source}`),
                        })}
                      </span>
                    )}
                  </div>
                  <p className="text-11 text-tertiary">
                    {t("workspace_settings.settings.groups.member_count", { count: department.member_count })}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  disabled={index === 0 || busyId !== null}
                  onClick={() => handleMove(department, -1)}
                  label="↑"
                  aria-label={t("workspace_settings.settings.departments.move_up")}
                />
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  disabled={index === departments.length - 1 || busyId !== null}
                  onClick={() => handleMove(department, 1)}
                  label="↓"
                  aria-label={t("workspace_settings.settings.departments.move_down")}
                />
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  onClick={() => setMembersOf(department)}
                  label={t("workspace_settings.settings.groups.members")}
                />
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  onClick={() => setFormState({ department })}
                  label={t("workspace_settings.settings.groups.edit")}
                />
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  disabled={busyId !== null}
                  onClick={() => handleUpdate(department, { is_active: !department.is_active })}
                  label={
                    department.is_active
                      ? t("workspace_settings.settings.departments.deactivate")
                      : t("workspace_settings.settings.departments.activate")
                  }
                />
                {department.can_delete && (
                  <Button
                    size="md"
                    stretch="auto"
                    variant="secondary"
                    onClick={() => setToDelete(department)}
                    label={t("delete")}
                  />
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {formState !== null && (
        <DepartmentFormModal
          key={formState.department?.id ?? "new"}
          department={formState.department}
          onClose={() => setFormState(null)}
          onSubmit={handleSubmit}
        />
      )}
      {isImportOpen && (
        <DepartmentImportModal groups={groups ?? []} onClose={() => setIsImportOpen(false)} onImport={handleImport} />
      )}
      <GroupMembersModal
        workspaceSlug={workspaceSlug}
        group={membersOf ? ((groups ?? []).find((group) => group.id === membersOf.id) ?? membersOf) : null}
        onClose={() => setMembersOf(null)}
        onChanged={() => mutate()}
      />
      <ConfirmDialog
        isOpen={toDelete !== null}
        handleClose={() => setToDelete(null)}
        handleSubmit={handleDelete}
        isSubmitting={isDeleting}
        title={t("workspace_settings.settings.groups.delete_title", { name: toDelete?.name ?? "" })}
        content={t("workspace_settings.settings.departments.delete_content")}
        primaryButtonText={{ loading: t("deleting"), default: t("delete") }}
        secondaryButtonText={t("cancel")}
      />
    </section>
  );
});
