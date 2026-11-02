/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { BoxesOutline, CloseOutline, StarOutline, TickOutline, UserOutline } from "@makeplane/propel/icons";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { EmptySpace, EmptySpaceItem } from "@/components/ui/empty-space";
// constants
import { PI_PLANE_REPO_URL, WORKSPACE_INVITATION } from "@plane/constants";
// helpers
import { EPageTypes } from "@/helpers/authentication.helper";
// hooks
import { useUser } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
// wrappers
import { AuthenticationWrapper } from "@/lib/wrappers/authentication-wrapper";
import { WorkspaceService } from "@/services/workspace.service";
import { useTranslation } from "@plane/i18n";
// services

// service initialization
const workspaceService = new WorkspaceService();

function WorkspaceInvitationPage() {
  const { t } = useTranslation();
  // router
  const router = useAppRouter();
  // query params
  const searchParams = useSearchParams();
  const invitation_id = searchParams.get("invitation_id");
  const slug = searchParams.get("slug");
  const token = searchParams.get("token");
  // store hooks
  const { data: currentUser } = useUser();

  const { data: invitationDetail, error } = useSWR(
    invitation_id && slug && WORKSPACE_INVITATION(invitation_id.toString()),
    invitation_id && slug
      ? () => workspaceService.getWorkspaceInvitation(slug.toString(), invitation_id.toString())
      : null
  );

  const handleAccept = () => {
    if (!invitationDetail) return;
    workspaceService
      .joinWorkspace(invitationDetail.workspace.slug, invitationDetail.id, {
        accepted: true,
        token: token,
      })
      .then(() => {
        if (invitationDetail.email === currentUser?.email) {
          router.push(`/${invitationDetail.workspace.slug}`);
        } else {
          router.push("/");
        }
        return;
      })
      .catch((err: unknown) => console.error(err));
  };

  const handleReject = () => {
    if (!invitationDetail || !token) return;
    void workspaceService
      .joinWorkspace(invitationDetail.workspace.slug, invitationDetail.id, {
        accepted: false,
        token: token,
      })
      .then(() => {
        router.push("/");
        return;
      })
      .catch((err: unknown) => console.error(err));
  };

  return (
    <AuthenticationWrapper pageType={EPageTypes.PUBLIC}>
      <div className="flex h-full w-full flex-col items-center justify-center px-3">
        {invitationDetail && !invitationDetail.responded_at ? (
          error ? (
            <div className="shadow-2xl flex w-full flex-col space-y-4 rounded-sm border border-subtle bg-surface-1 px-4 py-8 text-center md:w-1/3">
              <h2 className="text-18 uppercase">{t("core_ui.invitation.not_found")}</h2>
            </div>
          ) : (
            <EmptySpace
              title={t("core_ui.invitation.invited_to", { workspace: invitationDetail.workspace.name })}
              description={t("core_ui.invitation.description")}
            >
              <EmptySpaceItem Icon={TickOutline} title={t("core_ui.invitation.accept")} action={handleAccept} />
              <EmptySpaceItem Icon={CloseOutline} title={t("core_ui.invitation.ignore")} action={handleReject} />
            </EmptySpace>
          )
        ) : error || invitationDetail?.responded_at ? (
          invitationDetail?.accepted ? (
            <EmptySpace
              title={t("core_ui.invitation.already_member", { workspace: invitationDetail.workspace.name })}
              description={t("core_ui.invitation.description")}
            >
              <EmptySpaceItem Icon={BoxesOutline} title={t("core_ui.invitation.continue_home")} href="/" />
            </EmptySpace>
          ) : (
            <EmptySpace
              title={t("core_ui.invitation.link_inactive")}
              description={t("core_ui.invitation.description")}
              link={{ text: t("core_ui.invitation.start_empty_project"), href: "/" }}
            >
              {!currentUser ? (
                <EmptySpaceItem Icon={UserOutline} title={t("core_ui.invitation.sign_in_continue")} href="/" />
              ) : (
                <EmptySpaceItem Icon={BoxesOutline} title={t("core_ui.invitation.continue_home")} href="/" />
              )}
              <EmptySpaceItem Icon={StarOutline} title={t("core_ui.invitation.star_github")} href={PI_PLANE_REPO_URL} />
            </EmptySpace>
          )
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <LogoSpinner />
          </div>
        )}
      </div>
    </AuthenticationWrapper>
  );
}

export default observer(WorkspaceInvitationPage);
