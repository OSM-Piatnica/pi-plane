/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { SyntheticEvent } from "react";
import React, { useRef } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams, usePathname, useSearchParams } from "next/navigation";
import { CalendarOutline, InfoOutline, UserAltOutline, WorkItemsOutline } from "@makeplane/propel/icons";
// plane package imports
import { MODULE_STATUS, EUserPermissions, EUserPermissionsLevel, IS_FAVORITE_MENU_OPEN } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
import { LinearProgress } from "@makeplane/propel/components/linear-progress";
import { setPromiseToast, setToast } from "@plane/blocks/toast";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { IModule } from "@plane/types";
import { Card } from "@plane/blocks/card";
import { FavoriteStar } from "@plane/blocks/common";
import { DateRangeSelect } from "@/components/dropdowns/date-select";
import { getDate, renderFormattedPayloadDate, generateQueryParams } from "@plane/utils";
// components
import { handleTriggerKeyDown } from "@/components/common/trigger-guard";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { ModuleQuickActions } from "@/components/modules";
import { ModuleStatusDropdown } from "@/components/modules/module-status-dropdown";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useModule } from "@/hooks/store/use-module";
import { useUserPermissions, useUserProfile } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useTranslation } from "@plane/i18n";

type Props = {
  moduleId: string;
};

const handleEventPropagation = (e: SyntheticEvent<HTMLDivElement>) => {
  e.stopPropagation();
  e.preventDefault();
};

export const ModuleCardItem = observer(function ModuleCardItem(props: Props) {
  const { moduleId } = props;
  // refs
  const parentRef = useRef(null);
  // router
  const router = useAppRouter();
  const { workspaceSlug, projectId } = useParams();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  // store hooks
  const { allowPermissions } = useUserPermissions();
  const { getModuleById, addModuleToFavorites, removeModuleFromFavorites, updateModuleDetails } = useModule();
  const { getUserDetails } = useMember();
  const { data: userProfile } = useUserProfile();
  // local storage
  const { setValue: toggleFavoriteMenu, storedValue } = useLocalStorage<boolean>(IS_FAVORITE_MENU_OPEN, false);
  // derived values
  const moduleDetails = getModuleById(moduleId);
  const isEditingAllowed = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT
  );
  const isDisabled = !isEditingAllowed || !!moduleDetails?.archived_at;
  const renderIcon = Boolean(moduleDetails?.start_date) || Boolean(moduleDetails?.target_date);

  const { isMobile } = usePlatformOS();
  const { t } = useTranslation();
  const handleAddToFavorites = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    e.preventDefault();
    if (!workspaceSlug || !projectId) return;

    const addToFavoritePromise = addModuleToFavorites(workspaceSlug.toString(), projectId.toString(), moduleId).then(
      () => {
        if (!storedValue) toggleFavoriteMenu(true);
        return;
      }
    );

    setPromiseToast(addToFavoritePromise, {
      loading: t("module_ui.adding_to_favorites"),
      success: {
        title: t("toast.success"),
        message: () => t("module_ui.added_to_favorites"),
      },
      error: {
        title: t("toast.error"),
        message: () => t("module_ui.add_favorite_error"),
      },
    });
  };

  const handleRemoveFromFavorites = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    e.preventDefault();
    if (!workspaceSlug || !projectId) return;

    const removeFromFavoritePromise = removeModuleFromFavorites(
      workspaceSlug.toString(),
      projectId.toString(),
      moduleId
    );

    setPromiseToast(removeFromFavoritePromise, {
      loading: t("module_ui.removing_from_favorites"),
      success: {
        title: t("toast.success"),
        message: () => t("module_ui.removed_from_favorites"),
      },
      error: {
        title: t("toast.error"),
        message: () => t("module_ui.remove_favorite_error"),
      },
    });
  };

  const handleModuleDetailsChange = async (payload: Partial<IModule>) => {
    if (!workspaceSlug || !projectId) return;

    await updateModuleDetails(workspaceSlug.toString(), projectId.toString(), moduleId, payload)
      .then(() => {
        setToast({
          type: "success",
          title: t("toast.success"),
          message: t("entity.update.success", { entity: t("common.module") }),
        });
        return;
      })
      .catch((err) => {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: err?.detail ?? t("module_ui.update_error"),
        });
      });
  };

  const openModuleOverview = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    e.preventDefault();

    const query = generateQueryParams(searchParams, ["peekModule"]);
    if (searchParams.has("peekModule") && searchParams.get("peekModule") === moduleId) {
      router.push(`${pathname}?${query}`);
    } else {
      router.push(`${pathname}?${query && `${query}&`}peekModule=${moduleId}`);
    }
  };

  if (!moduleDetails) return null;

  const moduleTotalIssues =
    moduleDetails.backlog_issues +
    moduleDetails.unstarted_issues +
    moduleDetails.started_issues +
    moduleDetails.completed_issues +
    moduleDetails.cancelled_issues;

  const moduleCompletedIssues = moduleDetails.completed_issues;

  // const areYearsEqual = startDate.getFullYear() === endDate.getFullYear();

  const moduleStatus = MODULE_STATUS.find((status) => status.value === moduleDetails.status);

  const issueCount = moduleDetails
    ? !moduleTotalIssues || moduleTotalIssues === 0
      ? `0 work items`
      : moduleTotalIssues === moduleCompletedIssues
        ? `${moduleTotalIssues} Work item${moduleTotalIssues > 1 ? `s` : ``}`
        : `${moduleCompletedIssues}/${moduleTotalIssues} Work items`
    : `0 work items`;

  const moduleLeadDetails = moduleDetails.lead_id ? getUserDetails(moduleDetails.lead_id) : undefined;
  const progressValue = moduleTotalIssues > 0 ? (moduleCompletedIssues / moduleTotalIssues) * 100 : 0;

  return (
    <div className="relative" data-prevent-progress>
      <Link ref={parentRef} href={`/${workspaceSlug}/projects/${moduleDetails.project_id}/modules/${moduleDetails.id}`}>
        <Card>
          <div>
            <div className="flex items-center justify-between gap-2">
              <Tooltip label={moduleDetails.name} layout="stacked" disabled={isMobile}>
                <span className="truncate text-14 font-medium">{moduleDetails.name}</span>
              </Tooltip>
              {/* Ruling 38: guard both halves — the card root is a `Link`. */}
              <div
                className="flex items-center gap-2"
                role="presentation"
                onClick={handleEventPropagation}
                onKeyDown={handleTriggerKeyDown}
              >
                {moduleStatus && (
                  <ModuleStatusDropdown
                    isDisabled={isDisabled}
                    moduleDetails={moduleDetails}
                    handleModuleDetailsChange={handleModuleDetailsChange}
                  />
                )}
                <button onClick={openModuleOverview}>
                  <InfoOutline className="h-4 w-4 text-placeholder" />
                </button>
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-secondary">
                <WorkItemsOutline className="h-4 w-4 text-tertiary" />
                <span className="text-11 text-tertiary">{issueCount ?? "0 Work item"}</span>
              </div>
              {moduleLeadDetails ? (
                <span className="cursor-default">
                  <ButtonAvatars showTooltip={false} userIds={moduleLeadDetails?.id} />
                </span>
              ) : (
                <Tooltip label={t("module_ui.no_lead")}>
                  <UserAltOutline className="mx-1 h-4 w-4 text-tertiary" />
                </Tooltip>
              )}
            </div>
            <LinearProgress
              value={progressValue}
              size="md"
              variant="brand"
              showValue={false}
              aria-label={t("app_text.modules.module_progress")}
            />
            {/* Ruling 38: the whole card is a `Link`, so the trigger's click and keyboard
                activation must not reach it. */}
            <div
              className="flex items-center justify-between py-0.5"
              role="presentation"
              onClick={handleEventPropagation}
              onKeyDown={handleTriggerKeyDown}
            >
              <DateRangeSelect
                variant="select-ghost-md"
                className={`h-6 w-full gap-1.5 rounded-sm border-[0.5px] border-strong text-11 text-tertiary ${
                  isDisabled ? "cursor-not-allowed" : "cursor-pointer"
                }`}
                value={{
                  from: getDate(moduleDetails.start_date) ?? null,
                  to: getDate(moduleDetails.target_date) ?? null,
                }}
                onChange={(range) => {
                  void handleModuleDetailsChange({
                    start_date: range.from ? renderFormattedPayloadDate(range.from) : null,
                    target_date: range.to ? renderFormattedPayloadDate(range.to) : null,
                  });
                }}
                placeholder={`${t("start_date")} - ${t("end_date")}`}
                weekStartsOn={userProfile?.start_of_the_week}
                disabled={isDisabled}
                icon={renderIcon ? undefined : <CalendarOutline aria-hidden="true" />}
              />
            </div>
          </div>
        </Card>
      </Link>
      <div className="absolute right-4 bottom-[18px] flex items-center gap-1.5">
        {isEditingAllowed && (
          <FavoriteStar
            onClick={(e) => {
              if (moduleDetails.is_favorite) handleRemoveFromFavorites(e);
              else handleAddToFavorites(e);
            }}
            selected={!!moduleDetails.is_favorite}
          />
        )}
        {workspaceSlug && projectId && (
          <ModuleQuickActions
            parentRef={parentRef}
            moduleId={moduleId}
            projectId={projectId.toString()}
            workspaceSlug={workspaceSlug.toString()}
          />
        )}
      </div>
    </div>
  );
});
