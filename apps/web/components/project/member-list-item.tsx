/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
// components
import { DataTable } from "@/components/common/data-table";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { useProjectColumns } from "@/components/projects/settings/useProjectColumns";
import type { RowData } from "@/components/projects/settings/useProjectColumns";
// store
import type { IProjectMemberDetails } from "@/store/member/project/base-project-member.store";
// local imports
import { ConfirmProjectMemberRemove } from "./confirm-project-member-remove";

type Props = {
  memberDetails: (IProjectMemberDetails | null)[];
  projectId: string;
  workspaceSlug: string;
};

export const ProjectMemberListItem = observer(function ProjectMemberListItem(props: Props) {
  const { memberDetails, projectId, workspaceSlug } = props;
  // translation
  const { t } = useTranslation();
  // router
  const router = useAppRouter();
  // store hooks
  const { leaveProject } = useUserPermissions();
  const { data: currentUser } = useUser();
  const {
    project: { removeMemberFromProject, fetchProjectMembers },
  } = useMember();
  // helper hooks
  const { columns, removeMemberModal, setRemoveMemberModal } = useProjectColumns({
    projectId,
    workspaceSlug,
  });

  const hasGroupRole = (memberId: string) =>
    memberDetails.some((member) => member?.member.id === memberId && member.group_role != null);

  const handleRemove = async (memberId: string) => {
    if (!workspaceSlug || !projectId || !memberId) return;

    if (memberId === currentUser?.id) {
      await leaveProject(workspaceSlug.toString(), projectId.toString())
        .then(async () => {
          router.push(`/${workspaceSlug}/projects`);
          return;
        })
        .catch((err) => {
          setToast({
            type: "error",
            title: t("project_components.member_list_item.leave_error_title"),
            message: err?.error || t("something_went_wrong_please_try_again"),
          });
        });
    } else
      await removeMemberFromProject(workspaceSlug.toString(), projectId.toString(), memberId)
        // a person a group holds in the project stays, as a member through the group
        .then(() => (hasGroupRole(memberId) ? fetchProjectMembers(workspaceSlug, projectId) : undefined))
        .catch((err) =>
          setToast({
            type: "error",
            title: t("project_components.member_list_item.remove_error_title"),
            message: err?.error || t("something_went_wrong_please_try_again"),
          })
        );
  };

  if (!memberDetails) return null;
  return (
    <>
      {removeMemberModal && (
        <ConfirmProjectMemberRemove
          isOpen={removeMemberModal !== null}
          onClose={() => setRemoveMemberModal(null)}
          data={{ id: removeMemberModal.member.id, display_name: removeMemberModal.member.display_name || "" }}
          onSubmit={() => handleRemove(removeMemberModal.member.id)}
        />
      )}
      <DataTable<RowData>
        columns={columns}
        // The store rows carry an `IUserLite` member while the columns read the `IWorkspaceMember`
        // fields they share; the legacy table erased this with `any`.
        data={
          (memberDetails?.filter((member): member is IProjectMemberDetails => member !== null) ??
            []) as unknown as RowData[]
        }
        keyExtractor={(rowData) => rowData?.member.id ?? ""}
      />
    </>
  );
});
