/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import type { TUserGroup, TUserGroupFormData } from "@plane/types";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// services
import { userGroupService } from "@/services/user-group.service";
// local imports
import { GroupFormModal } from "./group-form-modal";
import { GroupMembersModal } from "./group-members-modal";

type Props = {
  workspaceSlug: string;
};

type TGroupNode = { group: TUserGroup; depth: number };

/** The groups as a flat list in tree order: every group is followed by the ones nested below it. */
function flattenTree(groups: TUserGroup[]): TGroupNode[] {
  const byParent = new Map<string | null, TUserGroup[]>();
  const ids = new Set(groups.map((group) => group.id));
  for (const group of groups) {
    // A group whose parent is not in the list is shown at the top, so it can never go missing
    const key = group.parent && ids.has(group.parent) ? group.parent : null;
    byParent.set(key, [...(byParent.get(key) ?? []), group]);
  }
  const result: TGroupNode[] = [];
  const walk = (parent: string | null, depth: number) => {
    for (const group of byParent.get(parent) ?? []) {
      result.push({ group, depth });
      walk(group.id, depth + 1);
    }
  };
  walk(null, 0);
  return result;
}

export const UserGroupsSettings = observer(function UserGroupsSettings(props: Props) {
  const { workspaceSlug } = props;
  // translation
  const { t } = useTranslation();
  // store hooks
  const { allowPermissions } = useUserPermissions();
  // states
  const [formState, setFormState] = useState<{ group?: TUserGroup; parentId?: string | null } | null>(null);
  const [membersOf, setMembersOf] = useState<TUserGroup | null>(null);
  const [groupToDelete, setGroupToDelete] = useState<TUserGroup | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const { data: groups, mutate } = useSWR(`USER_GROUPS_${workspaceSlug}`, () => userGroupService.list(workspaceSlug));

  // derived values
  const isWorkspaceAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const nodes = useMemo(() => flattenTree(groups ?? []), [groups]);
  const parentOptions = useMemo(
    () => (groups ?? []).filter((group) => group.can_manage && !group.is_external),
    [groups]
  );

  const showError = (error: unknown) =>
    setToast({
      type: "error",
      title: t("toast.error"),
      message: (error as { error?: string })?.error ?? t("something_went_wrong_please_try_again"),
    });

  const handleSubmit = async (data: TUserGroupFormData) => {
    try {
      if (formState?.group) {
        await userGroupService.update(workspaceSlug, formState.group.id, data);
      } else {
        await userGroupService.create(workspaceSlug, data);
      }
      await mutate();
      setToast({
        type: "success",
        title: t("toast.success"),
        message: formState?.group
          ? t("workspace_settings.settings.groups.group_updated")
          : t("workspace_settings.settings.groups.group_created"),
      });
    } catch (error) {
      showError(error);
      throw error;
    }
  };

  const handleDelete = async () => {
    if (!groupToDelete) return;
    setIsDeleting(true);
    try {
      await userGroupService.remove(workspaceSlug, groupToDelete.id);
      await mutate();
      setGroupToDelete(null);
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("workspace_settings.settings.groups.group_deleted"),
      });
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
          <h4 className="text-h3-medium">{t("workspace_settings.settings.groups.title")}</h4>
          <p className="text-13 text-secondary">{t("workspace_settings.settings.groups.description")}</p>
        </div>
        {(isWorkspaceAdmin || parentOptions.length > 0) && (
          <Button
            size="md"
            stretch="auto"
            variant="primary"
            onClick={() => setFormState({ parentId: null })}
            label={t("workspace_settings.settings.groups.create_group")}
          />
        )}
      </div>

      {groups && groups.length === 0 && (
        <div className="rounded-lg border border-subtle p-6 text-13 text-secondary">
          {t("workspace_settings.settings.groups.no_groups")}
        </div>
      )}

      <ul className="flex flex-col divide-y divide-subtle rounded-lg border border-subtle">
        {nodes.map(({ group, depth }) => (
          <li key={group.id} className="flex items-center justify-between gap-3 px-4 py-3">
            <div className="min-w-0" style={{ paddingInlineStart: `${depth * 24}px` }}>
              <div className="flex items-center gap-2">
                <span className="truncate text-14 font-medium text-primary">{group.name}</span>
                {group.is_external && (
                  <span className="rounded-full bg-layer-1 px-2 py-0.5 text-11 text-secondary">
                    {t("workspace_settings.settings.groups.managed_by", {
                      provider: t(`workspace_settings.settings.groups.sources.${group.source}`),
                    })}
                  </span>
                )}
              </div>
              {group.description && <p className="truncate text-13 text-secondary">{group.description}</p>}
              <p className="text-11 text-tertiary">
                {t("workspace_settings.settings.groups.member_count", { count: group.member_count })}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button
                size="md"
                stretch="auto"
                variant="secondary"
                onClick={() => setMembersOf(group)}
                label={t("workspace_settings.settings.groups.members")}
              />
              {group.can_manage && !group.is_external && (
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  onClick={() => setFormState({ parentId: group.id })}
                  label={t("workspace_settings.settings.groups.add_subgroup")}
                />
              )}
              {group.can_manage && !group.is_external && (
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  onClick={() => setFormState({ group })}
                  label={t("workspace_settings.settings.groups.edit")}
                />
              )}
              {group.can_delete && (
                <Button
                  size="md"
                  stretch="auto"
                  variant="secondary"
                  onClick={() => setGroupToDelete(group)}
                  label={t("delete")}
                />
              )}
            </div>
          </li>
        ))}
      </ul>

      <GroupFormModal
        isOpen={formState !== null}
        group={formState?.group}
        parentId={formState?.parentId}
        parentOptions={parentOptions}
        canCreateTopLevel={isWorkspaceAdmin}
        onClose={() => setFormState(null)}
        onSubmit={handleSubmit}
      />
      <GroupMembersModal
        workspaceSlug={workspaceSlug}
        group={membersOf ? ((groups ?? []).find((group) => group.id === membersOf.id) ?? membersOf) : null}
        onClose={() => setMembersOf(null)}
        onChanged={() => mutate()}
      />
      <ConfirmDialog
        isOpen={groupToDelete !== null}
        handleClose={() => setGroupToDelete(null)}
        handleSubmit={handleDelete}
        isSubmitting={isDeleting}
        title={t("workspace_settings.settings.groups.delete_title", { name: groupToDelete?.name ?? "" })}
        content={t("workspace_settings.settings.groups.delete_content")}
        primaryButtonText={{ loading: t("deleting"), default: t("delete") }}
        secondaryButtonText={t("cancel")}
      />
    </section>
  );
});
