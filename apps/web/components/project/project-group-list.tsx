/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EProjectGroupRole } from "@plane/types";
import type { TProjectGroup } from "@plane/types";
// helpers
import { PROJECT_GROUP_ROLES, getAddableGroups, isProjectGroupRole } from "@/helpers/project-group";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUserPermissions } from "@/hooks/store/user";
// services
import { projectGroupService } from "@/services/project/project-group.service";
import { userGroupService } from "@/services/user-group.service";

type Props = {
  workspaceSlug: string;
  projectId: string;
};

const SELECT_CLASS = "h-8 rounded-md border border-subtle bg-surface-1 px-2 text-13 text-secondary";

/** The groups that are members of the project, with their role, for project admins to change. */
export const ProjectGroupList = observer(function ProjectGroupList(props: Props) {
  const { workspaceSlug, projectId } = props;
  // translation
  const { t } = useTranslation();
  // store hooks
  const { allowPermissions } = useUserPermissions();
  const {
    project: { fetchProjectMembers },
  } = useMember();
  // states
  const [newGroupId, setNewGroupId] = useState("");
  const [newRole, setNewRole] = useState<EProjectGroupRole>(EProjectGroupRole.MEMBER);
  const [isAdding, setIsAdding] = useState(false);
  const [linkToRemove, setLinkToRemove] = useState<TProjectGroup | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);

  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);

  const { data: links, mutate } = useSWR(`PROJECT_GROUPS_${workspaceSlug}_${projectId}`, () =>
    projectGroupService.list(workspaceSlug, projectId)
  );
  // only admins pick a group to add, so only they need the workspace's groups
  const { data: groups } = useSWR(isAdmin ? `USER_GROUPS_${workspaceSlug}` : null, () =>
    userGroupService.list(workspaceSlug)
  );

  // derived values
  const addable = getAddableGroups(groups ?? [], links ?? []);
  const roleLabel = (role: EProjectGroupRole) =>
    role === EProjectGroupRole.GUEST ? t("project_members.groups.role_guest") : t("project_members.groups.role_member");

  const showError = (error: unknown) =>
    setToast({
      type: "error",
      title: t("toast.error"),
      message: (error as { error?: string })?.error ?? t("something_went_wrong_please_try_again"),
    });

  // a change to a group changes who is in the project, so the people list is fetched again
  const refresh = async () => {
    await Promise.all([mutate(), fetchProjectMembers(workspaceSlug, projectId)]);
  };

  const handleAdd = async () => {
    if (!newGroupId) return;
    setIsAdding(true);
    try {
      await projectGroupService.add(workspaceSlug, projectId, { group: newGroupId, role: newRole });
      setNewGroupId("");
      await refresh();
      setToast({ type: "success", title: t("toast.success"), message: t("project_members.groups.group_added") });
    } catch (error) {
      showError(error);
    } finally {
      setIsAdding(false);
    }
  };

  const handleRoleChange = async (link: TProjectGroup, role: EProjectGroupRole) => {
    try {
      await projectGroupService.updateRole(workspaceSlug, projectId, link.id, role);
      await refresh();
      setToast({ type: "success", title: t("toast.success"), message: t("project_members.groups.group_updated") });
    } catch (error) {
      showError(error);
    }
  };

  const handleRemove = async () => {
    if (!linkToRemove) return;
    setIsRemoving(true);
    try {
      await projectGroupService.remove(workspaceSlug, projectId, linkToRemove.id);
      setLinkToRemove(null);
      await refresh();
      setToast({ type: "success", title: t("toast.success"), message: t("project_members.groups.group_removed") });
    } catch (error) {
      showError(error);
    } finally {
      setIsRemoving(false);
    }
  };

  // people who are not admins have nothing to see or do when the project has no groups
  if (!isAdmin && (!links || links.length === 0)) return null;

  return (
    <section className="flex flex-col gap-3 pb-6">
      <div className="flex flex-col gap-1 border-b border-subtle py-2">
        <div className="text-14 font-semibold">{t("project_members.groups.title")}</div>
        <p className="text-13 text-secondary">{t("project_members.groups.description")}</p>
      </div>

      {links && links.length === 0 && (
        <div className="rounded-lg border border-subtle p-4 text-13 text-secondary">
          {t("project_members.groups.no_groups")}
        </div>
      )}

      {links && links.length > 0 && (
        <ul className="flex flex-col divide-y divide-subtle rounded-lg border border-subtle">
          {links.map((link) => (
            <li key={link.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-14 font-medium text-primary">{link.group_name}</span>
                  {link.group_source !== "local" && (
                    <span className="rounded-full bg-layer-1 px-2 py-0.5 text-11 text-secondary">
                      {t(`workspace_settings.settings.groups.sources.${link.group_source}`)}
                    </span>
                  )}
                </div>
                <p className="text-11 text-tertiary">
                  {t("project_members.groups.member_count", { count: link.member_count })}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {isAdmin ? (
                  <>
                    <select
                      aria-label={t("project_members.groups.role")}
                      value={link.role}
                      onChange={(event) => {
                        const role = Number(event.target.value);
                        if (isProjectGroupRole(role)) void handleRoleChange(link, role);
                      }}
                      className={SELECT_CLASS}
                    >
                      {PROJECT_GROUP_ROLES.map((role) => (
                        <option key={role} value={role}>
                          {roleLabel(role)}
                        </option>
                      ))}
                    </select>
                    <Button
                      size="md"
                      stretch="auto"
                      variant="secondary"
                      onClick={() => setLinkToRemove(link)}
                      label={t("remove")}
                    />
                  </>
                ) : (
                  <span className="text-13 text-secondary">{roleLabel(link.role)}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {isAdmin && (
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label={t("project_members.groups.select_group")}
            value={newGroupId}
            onChange={(event) => setNewGroupId(event.target.value)}
            className={SELECT_CLASS}
          >
            <option value="">
              {addable.length === 0 && groups
                ? t("project_members.groups.no_groups_available")
                : t("project_members.groups.select_group")}
            </option>
            {addable.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
          <select
            aria-label={t("project_members.groups.role")}
            value={newRole}
            onChange={(event) => {
              const role = Number(event.target.value);
              if (isProjectGroupRole(role)) setNewRole(role);
            }}
            className={SELECT_CLASS}
          >
            {PROJECT_GROUP_ROLES.map((role) => (
              <option key={role} value={role}>
                {roleLabel(role)}
              </option>
            ))}
          </select>
          <Button
            size="md"
            stretch="auto"
            variant="primary"
            onClick={handleAdd}
            disabled={!newGroupId || isAdding}
            label={t("project_members.groups.add_group")}
          />
        </div>
      )}

      <ConfirmDialog
        isOpen={linkToRemove !== null}
        handleClose={() => setLinkToRemove(null)}
        handleSubmit={handleRemove}
        isSubmitting={isRemoving}
        title={t("project_members.groups.remove_title", { name: linkToRemove?.group_name ?? "" })}
        content={t("project_members.groups.remove_content")}
        primaryButtonText={{ loading: t("removing"), default: t("remove") }}
        secondaryButtonText={t("cancel")}
      />
    </section>
  );
});
