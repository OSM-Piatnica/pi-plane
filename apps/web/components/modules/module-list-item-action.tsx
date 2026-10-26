/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { CalendarOutline, UserAltOutline } from "@makeplane/propel/icons";
// Plane imports
import { MODULE_STATUS, EUserPermissions, EUserPermissionsLevel, IS_FAVORITE_MENU_OPEN } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
import { useTranslation } from "@plane/i18n";
import { setPromiseToast, setToast } from "@plane/blocks/toast";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { IModule } from "@plane/types";
import { FavoriteStar } from "@plane/blocks/common";
import { DateRangeSelect } from "@/components/dropdowns/date-select";
import { renderFormattedPayloadDate, getDate } from "@plane/utils";
// components
import { ModuleQuickActions } from "@/components/modules";
import { ModuleStatusDropdown } from "@/components/modules/module-status-dropdown";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useModule } from "@/hooks/store/use-module";
import { useUserPermissions } from "@/hooks/store/user";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { ButtonAvatars } from "../dropdowns/member/avatar";

type Props = {
  moduleId: string;
  moduleDetails: IModule;
  parentRef: React.RefObject<HTMLDivElement | null>;
};

export const ModuleListItemAction = observer(function ModuleListItemAction(props: Props) {
  const { moduleId, moduleDetails, parentRef } = props;
  // router
  const { workspaceSlug, projectId } = useParams();
  //   store hooks
  const { allowPermissions } = useUserPermissions();
  const { addModuleToFavorites, removeModuleFromFavorites, updateModuleDetails } = useModule();
  const { getUserDetails } = useMember();
  const startOfTheWeek = useStartOfTheWeek();

  const { t } = useTranslation();

  // local storage
  const { setValue: toggleFavoriteMenu, storedValue } = useLocalStorage<boolean>(IS_FAVORITE_MENU_OPEN, false);
  // derived values

  const moduleStatus = MODULE_STATUS.find((status) => status.value === moduleDetails.status);
  const isEditingAllowed = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT
  );
  const isDisabled = !isEditingAllowed || !!moduleDetails?.archived_at;
  const renderIcon = Boolean(moduleDetails.start_date) || Boolean(moduleDetails.target_date);

  // handlers
  const handleAddToFavorites = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    e.preventDefault();
    if (!workspaceSlug || !projectId) return;

    const addToFavoritePromise = addModuleToFavorites(workspaceSlug.toString(), projectId.toString(), moduleId).then(
      () => {
        // open favorites menu if closed
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

  const moduleLeadDetails = moduleDetails.lead_id ? getUserDetails(moduleDetails.lead_id) : undefined;

  return (
    <>
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
        mergeDates
        placeholder={`${t("start_date")} - ${t("end_date")}`}
        weekStartsOn={startOfTheWeek}
        disabled={isDisabled}
        icon={renderIcon ? undefined : <CalendarOutline aria-hidden="true" />}
      />

      {moduleStatus && (
        <ModuleStatusDropdown
          isDisabled={isDisabled}
          moduleDetails={moduleDetails}
          handleModuleDetailsChange={handleModuleDetailsChange}
        />
      )}

      {moduleLeadDetails ? (
        <span className="cursor-default">
          <ButtonAvatars showTooltip={false} userIds={moduleLeadDetails?.id} />
        </span>
      ) : (
        <Tooltip label={t("module_ui.no_lead")}>
          <UserAltOutline className="h-4 w-4 text-tertiary" />
        </Tooltip>
      )}

      {isEditingAllowed && !moduleDetails.archived_at && (
        <FavoriteStar
          onClick={(e) => {
            if (moduleDetails.is_favorite) handleRemoveFromFavorites(e);
            else handleAddToFavorites(e);
          }}
          selected={moduleDetails.is_favorite}
        />
      )}
      {workspaceSlug && projectId && (
        <div className="hidden md:block">
          <ModuleQuickActions
            parentRef={parentRef}
            moduleId={moduleId}
            projectId={projectId.toString()}
            workspaceSlug={workspaceSlug.toString()}
          />
        </div>
      )}
    </>
  );
});
