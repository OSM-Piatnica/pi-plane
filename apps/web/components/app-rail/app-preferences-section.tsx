/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Checkbox } from "@makeplane/propel/components/checkbox";
import { DragDropOutline } from "@makeplane/propel/icons";
import { Sortable } from "@plane/blocks/common";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TAppRailAppKey } from "@plane/types";
import {
  arrangeAppRailApps,
  buildAppRailPreferenceUpdate,
  canHideAppRailApp,
  getAppRailDefaultAppKey,
} from "@plane/utils";
import type { TAppRailArrangement } from "@plane/utils";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { APP_RAIL_APP_ICONS } from "./registry-icons";
import { useAppRailApps } from "./use-app-rail-apps";

type TItem = TAppRailArrangement<TAppRailAppKey>["items"][number];

const NO_DEFAULT_APP = "";

/**
 * The "Apps" part of the customise navigation dialog: which apps the rail shows, in which order,
 * and which app the user lands in. It renders nothing unless more than one app is enabled for
 * the user, since with a single app there is nothing to arrange or choose.
 */
export const AppRailPreferencesSection = observer(function AppRailPreferencesSection() {
  const { workspaceSlug: routeWorkspaceSlug } = useParams();
  const { t } = useTranslation();
  const { enabledApps, hasMultipleApps } = useAppRailApps();
  const {
    getNavigationPreferences,
    updateBulkSidebarPreferences,
    getProjectNavigationPreferences,
    updateProjectNavigationPreferences,
  } = useWorkspace();

  const workspaceSlug = routeWorkspaceSlug?.toString();
  if (!workspaceSlug || !hasMultipleApps) return null;

  const { items } = arrangeAppRailApps(enabledApps, getNavigationPreferences(workspaceSlug));
  const defaultAppKey = getAppRailDefaultAppKey(
    enabledApps,
    getProjectNavigationPreferences(workspaceSlug)?.default_app
  );

  const showError = () =>
    setToast({ type: "error", title: t("toast.error"), message: t("something_went_wrong_please_try_again") });

  const saveArrangement = (nextItems: readonly TItem[]) => {
    updateBulkSidebarPreferences(workspaceSlug, buildAppRailPreferenceUpdate(nextItems)).catch(showError);
  };

  const toggleApp = (appKey: TAppRailAppKey, isShown: boolean) =>
    saveArrangement(items.map((item) => (item.app.key === appKey ? { ...item, isHidden: !isShown } : item)));

  const saveDefaultApp = (appKey: string) => {
    updateProjectNavigationPreferences(workspaceSlug, { default_app: appKey || null }).catch(showError);
  };

  const defaultAppOptions = [
    { value: NO_DEFAULT_APP, label: t("app_rail.preferences.last_used_app") },
    ...enabledApps.map((app) => ({ value: app.key as string, label: t(app.i18n_label) })),
  ];

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-13 font-semibold text-placeholder">{t("app_rail.preferences.heading")}</h3>
      <div className="rounded-md border border-subtle bg-surface-2 py-2">
        <Sortable
          data={items}
          onChange={saveArrangement}
          keyExtractor={(item) => item.app.key}
          id="app-rail-apps"
          render={(item) => {
            const Icon = APP_RAIL_APP_ICONS[item.app.key];
            return (
              <div className="flex items-center gap-2 rounded-md px-2 py-1.5 transition-all duration-200 hover:bg-surface-2">
                <DragDropOutline className="size-4 cursor-grab text-placeholder transition-colors active:cursor-grabbing" />
                <Checkbox
                  checked={!item.isHidden}
                  disabled={!item.isHidden && !canHideAppRailApp(items, item.app.key)}
                  onCheckedChange={(checked) => toggleApp(item.app.key, checked)}
                  aria-label={t(item.app.i18n_label)}
                />
                <div className="flex flex-1 items-center gap-2">
                  <Icon className="size-4" />
                  <span className="text-13 text-primary">{t(item.app.i18n_label)}</span>
                </div>
              </div>
            );
          }}
        />
      </div>
      <fieldset className="rounded-md border border-subtle bg-surface-2 px-2 py-2">
        <legend className="sr-only">{t("app_rail.preferences.default_app")}</legend>
        <div className="px-2 py-1.5">
          <div className="text-13 text-primary">{t("app_rail.preferences.default_app")}</div>
          <div className="text-11 text-secondary">{t("app_rail.preferences.default_app_description")}</div>
        </div>
        {defaultAppOptions.map((option) => (
          <label
            key={option.value}
            className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 hover:bg-surface-2"
          >
            <input
              type="radio"
              name="app-rail-default-app"
              value={option.value}
              checked={(defaultAppKey ?? NO_DEFAULT_APP) === option.value}
              onChange={() => saveDefaultApp(option.value)}
              className="size-4 text-accent-primary focus:ring-accent-strong"
            />
            <span className="text-13 text-primary">{option.label}</span>
          </label>
        ))}
      </fieldset>
    </div>
  );
});
