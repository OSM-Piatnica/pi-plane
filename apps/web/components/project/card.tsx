/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React, { useRef, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  DeleteOutline,
  LinkOutline,
  LockOutline,
  NewTabOutline,
  RestoreOutline,
  SettingsOutline,
  TickOutline,
  UserPlusOutline,
} from "@makeplane/propel/icons";
// plane imports
import { EUserPermissions, EUserPermissionsLevel, IS_FAVORITE_MENU_OPEN } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
import { Avatar } from "@makeplane/propel/components/avatar";
import { AvatarGroup } from "@makeplane/propel/components/avatar-group";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Logo } from "@plane/blocks/emoji-icon-picker";
import { setPromiseToast, setToast } from "@plane/blocks/toast";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { IProject } from "@plane/types";
import type { TContextMenuItem } from "@plane/blocks/context-menu";
import { ContextMenu } from "@plane/blocks/context-menu";
import { FavoriteStar } from "@plane/blocks/common";
import { copyUrlToClipboard, cn, getFileURL } from "@plane/utils";
// components
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { usePlatformOS } from "@/hooks/use-platform-os";
// local imports
import { CoverImage } from "@/components/common/cover-image";
import { DeleteProjectModal } from "./delete-project-modal";
import { JoinProjectModal } from "./join-project-modal";
import { ArchiveRestoreProjectModal } from "./archive-restore-modal";
import { useTranslation } from "@plane/i18n";
import { useLocalizedDates } from "@/hooks/use-localized-dates";

type Props = {
  project: IProject;
};

export const ProjectCard = observer(function ProjectCard(props: Props) {
  const { project } = props;
  // translation
  const { t } = useTranslation();
  const { formatDate } = useLocalizedDates();
  // states
  const [deleteProjectModalOpen, setDeleteProjectModal] = useState(false);
  const [joinProjectModalOpen, setJoinProjectModal] = useState(false);
  const [restoreProject, setRestoreProject] = useState(false);
  // refs
  const projectCardRef = useRef(null);
  // router
  const router = useAppRouter();
  const { workspaceSlug } = useParams();
  // store hooks
  const { getUserDetails } = useMember();
  const { addProjectToFavorites, removeProjectFromFavorites } = useProject();
  const { allowPermissions } = useUserPermissions();
  // hooks
  const { isMobile } = usePlatformOS();
  // derived values
  const projectMembers = (project.members ?? []).flatMap((memberId) => {
    const member = getUserDetails(memberId);
    return member ? [member] : [];
  });
  const shouldRenderFavorite = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );
  // auth
  const isMemberOfProject = !!project.member_role;
  const hasAdminRole = project.member_role === EUserPermissions.ADMIN;
  const hasMemberRole = project.member_role === EUserPermissions.MEMBER;
  // archive
  const isArchived = !!project.archived_at;
  // local storage
  const { setValue: toggleFavoriteMenu, storedValue: isFavoriteMenuOpen } = useLocalStorage<boolean>(
    IS_FAVORITE_MENU_OPEN,
    false
  );

  const handleAddToFavorites = () => {
    if (!workspaceSlug) return;

    const addToFavoritePromise = addProjectToFavorites(workspaceSlug.toString(), project.id);
    setPromiseToast(addToFavoritePromise, {
      loading: t("project_components.card.adding_to_favorites"),
      success: {
        title: t("toast.success"),
        message: () => t("project_components.card.added_to_favorites"),
        // propel: the callback exists for its side effect; a toast action is data, and there is
        // none here, so it returns an empty list rather than an empty fragment.
        actionItems: () => {
          if (!isFavoriteMenuOpen) toggleFavoriteMenu(true);
          return [];
        },
      },
      error: {
        title: t("toast.error"),
        message: () => t("couldnt_add_the_project_to_favorites"),
      },
    });
  };

  const handleRemoveFromFavorites = () => {
    if (!workspaceSlug) return;

    const removeFromFavoritePromise = removeProjectFromFavorites(workspaceSlug.toString(), project.id);
    setPromiseToast(removeFromFavoritePromise, {
      loading: t("project_components.card.removing_from_favorites"),
      success: {
        title: t("toast.success"),
        message: () => t("project_components.card.removed_from_favorites"),
      },
      error: {
        title: t("toast.error"),
        message: () => t("couldnt_remove_the_project_from_favorites"),
      },
    });
  };

  const projectLink = `${workspaceSlug}/projects/${project.id}/issues`;
  const handleCopyText = () =>
    copyUrlToClipboard(projectLink).then(() =>
      setToast({
        type: "info",
        title: t("common.link_copied"),
        message: t("project_components.card.link_copied_message"),
      })
    );
  const handleOpenInNewTab = () => window.open(`/${projectLink}`, "_blank", "noopener,noreferrer");

  const MENU_ITEMS: TContextMenuItem[] = [
    {
      key: "settings",
      action: () => router.push(`/${workspaceSlug}/settings/projects/${project.id}`),
      title: t("settings"),
      icon: SettingsOutline,
      shouldRender: !isArchived && (hasAdminRole || hasMemberRole),
    },
    {
      key: "join",
      action: () => setJoinProjectModal(true),
      title: t("common.join"),
      icon: UserPlusOutline,
      shouldRender: !isMemberOfProject && !isArchived,
    },
    {
      key: "open-new-tab",
      action: handleOpenInNewTab,
      title: t("open_in_new_tab"),
      icon: NewTabOutline,
      shouldRender: !isMemberOfProject && !isArchived,
    },
    {
      key: "copy-link",
      action: () => void handleCopyText(),
      title: t("copy_link"),
      icon: LinkOutline,
      shouldRender: !isArchived,
    },
    {
      key: "restore",
      action: () => setRestoreProject(true),
      title: t("restore"),
      icon: RestoreOutline,
      shouldRender: isArchived && hasAdminRole,
    },
    {
      key: "delete",
      action: () => setDeleteProjectModal(true),
      title: t("delete"),
      icon: DeleteOutline,
      shouldRender: isArchived && hasAdminRole,
    },
  ];

  return (
    <>
      {/* Delete Project Modal */}
      <DeleteProjectModal
        project={project}
        isOpen={deleteProjectModalOpen}
        onClose={() => setDeleteProjectModal(false)}
      />
      {/* Join Project Modal */}
      {workspaceSlug && (
        <JoinProjectModal
          workspaceSlug={workspaceSlug.toString()}
          project={project}
          isOpen={joinProjectModalOpen}
          handleClose={() => setJoinProjectModal(false)}
        />
      )}
      {/* Restore project modal */}
      {workspaceSlug && project && (
        <ArchiveRestoreProjectModal
          workspaceSlug={workspaceSlug.toString()}
          projectId={project.id}
          isOpen={restoreProject}
          onClose={() => setRestoreProject(false)}
          archive={false}
        />
      )}
      <Link
        ref={projectCardRef}
        href={`/${workspaceSlug}/projects/${project.id}/issues`}
        onClick={(e) => {
          if (!isMemberOfProject || isArchived) {
            e.preventDefault();
            e.stopPropagation();
            if (!isArchived) setJoinProjectModal(true);
          }
        }}
        data-prevent-progress={!isMemberOfProject || isArchived}
        className={cn(
          "group/project-card flex w-full flex-col justify-between overflow-hidden rounded-lg border border-subtle bg-layer-2 transition-all duration-300 hover:border-strong hover:shadow-raised-200"
        )}
      >
        <ContextMenu parentRef={projectCardRef} items={MENU_ITEMS} />
        <div className="relative h-[118px] w-full rounded-t">
          <div className="absolute inset-0 z-[1] bg-gradient-to-t from-black/60 to-transparent" />

          <CoverImage
            src={project.cover_image_url}
            alt={project.name}
            className="absolute top-0 left-0 h-full w-full rounded-t"
          />

          <div className="absolute bottom-4 z-[1] flex h-10 w-full items-center justify-between gap-3 px-4">
            <div className="flex flex-grow items-center gap-2.5 truncate">
              <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-sm bg-white/10">
                <Logo logo={project.logo_props} size={18} />
              </div>

              <div className="flex w-full flex-col justify-between gap-0.5 truncate">
                <h3 className="truncate font-semibold text-on-color">{project.name}</h3>
                <span className="flex items-center gap-1.5">
                  <p className="text-11 font-medium text-on-color">{project.identifier} </p>
                  {project.network === 0 && <LockOutline className="h-2.5 w-2.5 text-on-color" />}
                </span>
              </div>
            </div>

            {!isArchived && (
              <div data-prevent-progress className="flex h-full flex-shrink-0 items-center gap-2">
                <button
                  type="button"
                  aria-label={t("common.actions.copy_link")}
                  className="flex h-6 w-6 items-center justify-center rounded-sm bg-white/10"
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    void handleCopyText();
                  }}
                >
                  <LinkOutline className="h-3 w-3 text-on-color" />
                </button>
                {shouldRenderFavorite && (
                  <FavoriteStar
                    buttonClassName="h-6 w-6 bg-white/10 rounded-sm"
                    iconClassName={cn("h-3 w-3", {
                      "text-on-color": !project.is_favorite,
                    })}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      if (project.is_favorite) handleRemoveFromFavorites();
                      else handleAddToFavorites();
                    }}
                    selected={!!project.is_favorite}
                  />
                )}
              </div>
            )}
          </div>
        </div>

        <div
          className={cn("flex h-[104px] w-full flex-col justify-between rounded-b-sm p-4", {
            "opacity-90": isArchived,
          })}
        >
          <p className="line-clamp-2 text-13 break-words text-tertiary">
            {project.description && project.description.trim() !== ""
              ? project.description
              : t("project_components.card.created_on", { date: formatDate(project.created_at) })}
          </p>
          <div className="item-center flex justify-between">
            <div className="flex items-center justify-center gap-2">
              <Tooltip
                disabled={isMobile}
                label={`${t("members")}: ${
                  project.members && project.members.length > 0
                    ? t("member", { count: project.members.length })
                    : t("project_components.card.no_member")
                }`}
                side="top"
              >
                {projectMembers.length > 0 ? (
                  <div className="flex cursor-pointer items-center gap-2 text-secondary">
                    <AvatarGroup size="xs" max={2}>
                      {projectMembers.map((member) => (
                        <Avatar
                          key={member.id}
                          alt={member.display_name}
                          fallback={member.display_name?.[0]?.toUpperCase()}
                          src={getFileURL(member.avatar_url)}
                        />
                      ))}
                    </AvatarGroup>
                  </div>
                ) : (
                  <span className="text-13 text-placeholder italic">{t("project_components.card.no_member_yet")}</span>
                )}
              </Tooltip>
              {isArchived && (
                <div className="text-11 font-medium text-placeholder">{t("project_components.shared.archived")}</div>
              )}
            </div>
            {isArchived ? (
              hasAdminRole && (
                <div className="flex items-center justify-center gap-2">
                  {/* oxlint-disable-next-line click-events-have-key-events, no-static-element-interactions -- existing behaviour; lint cleanup only */}
                  <Button
                    variant="ghost"
                    size="xs"
                    stretch="auto"
                    label={t("restore")}
                    icon={<Icon icon={RestoreOutline} />}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setRestoreProject(true);
                    }}
                  />
                  <IconButton
                    variant="ghost"
                    size="xs"
                    aria-label={t("common.actions.delete")}
                    icon={<Icon icon={DeleteOutline} />}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setDeleteProjectModal(true);
                    }}
                  />
                </div>
              )
            ) : (
              <>
                {isMemberOfProject &&
                  (hasAdminRole || hasMemberRole ? (
                    <Link
                      className="flex items-center justify-center rounded-sm p-1 text-placeholder hover:bg-layer-1 hover:text-secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      href={`/${workspaceSlug}/settings/projects/${project.id}`}
                    >
                      <SettingsOutline className="h-3.5 w-3.5" />
                    </Link>
                  ) : (
                    <span className="flex items-center gap-1 text-13 text-placeholder">
                      <TickOutline className="h-3.5 w-3.5" />
                      {t("project_components.shared.joined")}
                    </span>
                  ))}
                {!isMemberOfProject && (
                  <div className="flex items-center">
                    <Button
                      variant="ghost"
                      size="sm"
                      stretch="auto"
                      label={t("common.join")}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setJoinProjectModal(true);
                      }}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </Link>
    </>
  );
});
