/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { EmptyStateDetailed } from "@plane/blocks/empty-state";

type TProps = {
  isWorkspaceAdmin: boolean;
  handleJoinProject: () => void;
  isJoinButtonDisabled: boolean;
  errorStatusCode: number | undefined;
  /** The project is Private: it is listed for the workspace but locked until an admin lets the user in. */
  isPrivateLocked?: boolean;
  /** The user already asked for access and no admin has answered yet. */
  hasPendingRequest?: boolean;
  onRequestAccess?: () => void;
};

export const ProjectAccessRestriction = observer(function ProjectAccessRestriction(props: TProps) {
  const {
    isWorkspaceAdmin,
    handleJoinProject,
    isJoinButtonDisabled,
    errorStatusCode,
    isPrivateLocked = false,
    hasPendingRequest = false,
    onRequestAccess,
  } = props;
  // plane hooks
  const { t } = useTranslation();

  // Show join project screen if:
  // - User lacks project membership (409 Conflict)
  // - User lacks permission to access the private project (403 Forbidden) but is a workspace admin (can join any project)
  if (errorStatusCode === 409 || (errorStatusCode === 403 && isWorkspaceAdmin))
    return (
      <div className="grid h-full w-full place-items-center bg-surface-1">
        <EmptyStateDetailed
          title={t("project_empty_state.no_access.title")}
          description={t("project_empty_state.no_access.join_description")}
          assetKey="no-access"
          assetClassName="size-40"
          actions={[
            {
              label: isJoinButtonDisabled
                ? t("project_empty_state.no_access.cta_loading")
                : t("project_empty_state.no_access.cta_primary"),
              onClick: handleJoinProject,
              disabled: isJoinButtonDisabled,
            },
          ]}
        />
      </div>
    );

  // Show the request access screen for a Private project (listed, but locked until an admin lets the user in)
  if (errorStatusCode === 403 && isPrivateLocked) {
    return (
      <div className="grid h-full w-full place-items-center bg-surface-1">
        <EmptyStateDetailed
          title={
            hasPendingRequest
              ? t("project_empty_state.no_access.pending_title")
              : t("project_empty_state.no_access.private_title")
          }
          description={
            hasPendingRequest
              ? t("project_empty_state.no_access.pending_description")
              : t("project_empty_state.no_access.private_description")
          }
          assetKey="no-access"
          assetClassName="size-40"
          actions={
            hasPendingRequest || !onRequestAccess
              ? undefined
              : [{ label: t("project_empty_state.no_access.request_cta"), onClick: onRequestAccess }]
          }
        />
      </div>
    );
  }

  // Show no access screen if:
  // - User lacks permission to access the secret project (403 Forbidden)
  if (errorStatusCode === 403) {
    return (
      <div className="grid h-full w-full place-items-center bg-surface-1">
        <EmptyStateDetailed
          title={t("project_empty_state.no_access.title")}
          description={t("project_empty_state.no_access.restricted_description")}
          assetKey="no-access"
          assetClassName="size-40"
        />
      </div>
    );
  }

  // Show empty state screen if:
  // - Project not found (404 Not Found)
  // - Any other error status code
  return (
    <div className="grid h-full w-full place-items-center bg-surface-1">
      <EmptyStateDetailed
        title={t("project_empty_state.invalid_project.title")}
        description={t("project_empty_state.invalid_project.description")}
        assetKey="project"
        assetClassName="size-40"
      />
    </div>
  );
});
