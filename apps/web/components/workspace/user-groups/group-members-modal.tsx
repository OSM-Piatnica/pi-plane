/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { setToast } from "@plane/blocks/toast";
import { EUserGroupRole } from "@plane/types";
import type { TUserGroup } from "@plane/types";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import { userGroupService } from "@/services/user-group.service";

type Props = {
  workspaceSlug: string;
  group: TUserGroup | null;
  onClose: () => void;
  /** The member counts of the list change when somebody joins or leaves. */
  onChanged: () => void;
};

const SELECT_CLASSNAME = "h-9 rounded-md border border-subtle bg-surface-1 px-2 text-13 text-primary";

export const GroupMembersModal = observer(function GroupMembersModal(props: Props) {
  const { workspaceSlug, group, onClose, onChanged } = props;
  // translation
  const { t } = useTranslation();
  // store hooks
  const {
    getUserDetails,
    workspace: { workspaceMemberIds },
  } = useMember();
  // states
  const [newMemberId, setNewMemberId] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<EUserGroupRole>(EUserGroupRole.MEMBER);
  const [isWorking, setIsWorking] = useState(false);

  const { data: members, mutate } = useSWR(group ? `USER_GROUP_MEMBERS_${workspaceSlug}_${group.id}` : null, () =>
    group ? userGroupService.listMembers(workspaceSlug, group.id) : undefined
  );

  // derived values
  const canEdit = Boolean(group?.can_manage) && !group?.is_external;
  const memberUserIds = useMemo(() => new Set((members ?? []).map((member) => member.user.id)), [members]);
  const candidates = (workspaceMemberIds ?? [])
    .map((id) => getUserDetails(id))
    .filter((user) => user && !user.is_bot && !memberUserIds.has(user.id));

  const run = async (action: () => Promise<unknown>) => {
    setIsWorking(true);
    try {
      await action();
      await mutate();
      onChanged();
    } catch (error) {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: (error as { error?: string })?.error ?? t("something_went_wrong_please_try_again"),
      });
    } finally {
      setIsWorking(false);
    }
  };

  const handleAdd = async () => {
    if (!group || !newMemberId) return;
    await run(() => userGroupService.addMember(workspaceSlug, group.id, { user_id: newMemberId, role: newMemberRole }));
    setNewMemberId("");
    setNewMemberRole(EUserGroupRole.MEMBER);
  };

  return (
    <Dialog
      open={Boolean(group)}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="lg">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>
                {t("workspace_settings.settings.groups.members_of", { name: group?.name ?? "" })}
              </DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            <div className="flex flex-col gap-4">
              {group?.is_external && (
                <p className="rounded-md bg-layer-1 p-3 text-13 text-secondary">
                  {t("workspace_settings.settings.groups.managed_externally_hint")}
                </p>
              )}
              {canEdit && (
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label={t("workspace_settings.settings.groups.select_member")}
                    value={newMemberId}
                    onChange={(event) => setNewMemberId(event.target.value)}
                    className={`${SELECT_CLASSNAME} min-w-56 flex-1`}
                  >
                    <option value="">{t("workspace_settings.settings.groups.select_member")}</option>
                    {candidates.map((user) => (
                      <option key={user?.id} value={user?.id}>
                        {user?.display_name}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label={t("workspace_settings.settings.groups.role")}
                    value={newMemberRole}
                    onChange={(event) => setNewMemberRole(Number(event.target.value) as EUserGroupRole)}
                    className={SELECT_CLASSNAME}
                  >
                    <option value={EUserGroupRole.MEMBER}>{t("workspace_settings.settings.groups.role_member")}</option>
                    <option value={EUserGroupRole.ADMIN}>{t("workspace_settings.settings.groups.role_admin")}</option>
                  </select>
                  <Button
                    size="md"
                    stretch="auto"
                    variant="primary"
                    onClick={handleAdd}
                    disabled={!newMemberId || isWorking}
                    label={t("workspace_settings.settings.groups.add_member")}
                  />
                </div>
              )}
              {members && members.length === 0 && (
                <p className="text-13 text-secondary">{t("workspace_settings.settings.groups.no_members")}</p>
              )}
              <ul className="flex max-h-96 flex-col divide-y divide-subtle overflow-y-auto">
                {(members ?? []).map((member) => (
                  <li key={member.id} className="flex items-center justify-between gap-3 py-2">
                    <span className="truncate text-13 text-primary">{member.user.display_name}</span>
                    <span className="flex items-center gap-2">
                      {canEdit && !member.managed_externally ? (
                        <select
                          aria-label={t("workspace_settings.settings.groups.role")}
                          value={member.role}
                          disabled={isWorking}
                          onChange={(event) =>
                            run(() =>
                              userGroupService.updateMemberRole(
                                workspaceSlug,
                                group!.id,
                                member.user.id,
                                Number(event.target.value) as EUserGroupRole
                              )
                            )
                          }
                          className={SELECT_CLASSNAME}
                        >
                          <option value={EUserGroupRole.MEMBER}>
                            {t("workspace_settings.settings.groups.role_member")}
                          </option>
                          <option value={EUserGroupRole.ADMIN}>
                            {t("workspace_settings.settings.groups.role_admin")}
                          </option>
                        </select>
                      ) : (
                        <span className="text-13 text-secondary">
                          {member.role === EUserGroupRole.ADMIN
                            ? t("workspace_settings.settings.groups.role_admin")
                            : t("workspace_settings.settings.groups.role_member")}
                        </span>
                      )}
                      {canEdit && !member.managed_externally && (
                        <Button
                          size="md"
                          stretch="auto"
                          variant="secondary"
                          disabled={isWorking}
                          onClick={() =>
                            run(() => userGroupService.removeMember(workspaceSlug, group!.id, member.user.id))
                          }
                          label={t("remove")}
                        />
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </DialogBody>
        </DialogMain>
      </DialogContent>
    </Dialog>
  );
});
