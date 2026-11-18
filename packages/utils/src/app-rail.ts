/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import {
  APP_RAIL_MAX_SWITCH_SHORTCUTS,
  APP_RAIL_NON_APP_ROUTE_SEGMENTS,
  APP_RAIL_SWITCH_KEY_SEQUENCE_PREFIX,
} from "@plane/constants";
import type { TAppRailApp, TAppRailContext } from "@plane/types";

/** Apps offered in this context, in registry order */
export const getEnabledAppRailApps = <TKey extends string>(
  apps: readonly TAppRailApp<TKey>[],
  context: TAppRailContext
): TAppRailApp<TKey>[] => apps.filter((app) => app.isEnabled(context));

/**
 * The rail, the switch commands and their shortcuts exist only when there is something to
 * switch between. With a single enabled app the shell looks as it did before the registry.
 */
export const hasMultipleAppRailApps = (enabledApps: readonly unknown[]): boolean => enabledApps.length > 1;

/** Path segments after the workspace slug, or undefined when the path is not under the workspace */
const getWorkspacePathSegments = (pathname: string, workspaceSlug: string): string[] | undefined => {
  const segments = pathname.split(/[?#]/)[0].split("/").filter(Boolean);
  return segments[0] === workspaceSlug ? segments.slice(1) : undefined;
};

/**
 * The app the current route belongs to, among the given (enabled) apps.
 *
 * - `/:workspaceSlug/settings/...` and `/:workspaceSlug/notifications/...` belong to no app.
 * - A path whose first segment an app lists in `routeSegments` belongs to that app.
 * - Everything else belongs to the default app. That includes routes rendered in the
 *   workspace shell without the slug in the URL (the compact `/i/:workItem` link).
 *
 * Segments are compared whole, so `/acme/approvals-archive` is not the `approvals` app.
 */
export const getActiveAppRailAppKey = <TKey extends string>(
  apps: readonly TAppRailApp<TKey>[],
  pathname: string,
  workspaceSlug: string | undefined
): TKey | undefined => {
  if (!workspaceSlug) return undefined;
  const defaultAppKey = apps.find((app) => app.isDefault)?.key;
  const firstSegment = getWorkspacePathSegments(pathname, workspaceSlug)?.[0];
  if (firstSegment === undefined) return defaultAppKey;
  if (APP_RAIL_NON_APP_ROUTE_SEGMENTS.includes(firstSegment)) return undefined;
  return apps.find((app) => app.routeSegments.includes(firstSegment))?.key ?? defaultAppKey;
};

/** Key sequence that switches to the app at this position of the rail (0-based), if it has one */
export const getAppRailSwitchKeySequence = (index: number): string | undefined =>
  index >= 0 && index < APP_RAIL_MAX_SWITCH_SHORTCUTS
    ? `${APP_RAIL_SWITCH_KEY_SEQUENCE_PREFIX}${index + 1}`
    : undefined;

/**
 * Problems in a registry that the type system cannot catch. Returns one message per problem;
 * an empty list means the registry is consistent. Used by the registry's unit test.
 */
export const validateAppRailApps = (apps: readonly TAppRailApp<string>[]): string[] => {
  const problems: string[] = [];
  const seenKeys = new Set<string>();
  const segmentOwners = new Map<string, string>();

  const defaultApps = apps.filter((app) => app.isDefault);
  if (defaultApps.length !== 1) problems.push(`expected exactly one default app, found ${defaultApps.length}`);

  for (const app of apps) {
    if (seenKeys.has(app.key)) problems.push(`duplicate app key "${app.key}"`);
    seenKeys.add(app.key);

    if (!app.isDefault && app.routeSegments.length === 0)
      problems.push(`app "${app.key}" owns no route segment and is not the default app`);

    for (const segment of app.routeSegments) {
      if (APP_RAIL_NON_APP_ROUTE_SEGMENTS.includes(segment))
        problems.push(`app "${app.key}" claims the reserved route segment "${segment}"`);
      const owner = segmentOwners.get(segment);
      if (owner) problems.push(`route segment "${segment}" is claimed by "${owner}" and "${app.key}"`);
      else segmentOwners.set(segment, app.key);
    }
  }

  return problems;
};

export type TAppRailState<TKey extends string> = {
  /** Apps offered in this context, in registry order */
  enabledApps: TAppRailApp<TKey>[];
  /** The enabled app the current route belongs to */
  activeAppKey: TKey | undefined;
  /** False with a single enabled app: no rail, no switch commands, no shortcuts */
  hasMultipleApps: boolean;
};

/** Everything the shell derives from the registry for one workspace, user and route */
export const getAppRailState = <TKey extends string>(
  apps: readonly TAppRailApp<TKey>[],
  context: TAppRailContext,
  pathname: string
): TAppRailState<TKey> => {
  const enabledApps = getEnabledAppRailApps(apps, context);
  return {
    enabledApps,
    activeAppKey: getActiveAppRailAppKey(enabledApps, pathname, context.workspaceSlug),
    hasMultipleApps: hasMultipleAppRailApps(enabledApps),
  };
};

export type TAppRailDockItem<TKey extends string> = {
  key: TKey;
  i18n_label: string;
  href: string;
  isActive: boolean;
};

/** The rail items of the enabled apps, in rail order, without their React parts */
export const getAppRailDockItems = <TKey extends string>(
  state: Pick<TAppRailState<TKey>, "enabledApps" | "activeAppKey">,
  workspaceSlug: string
): TAppRailDockItem<TKey>[] =>
  state.enabledApps.map((app) => ({
    key: app.key,
    i18n_label: app.i18n_label,
    href: app.getHref(workspaceSlug),
    isActive: state.activeAppKey === app.key,
  }));

export type TAppRailRouteAccess = { isAllowed: true } | { isAllowed: false; redirectTo: string | undefined };

/**
 * Whether a route of the given app may render. An app that is not enabled for the user must not
 * be reachable by typing its URL: the answer then carries where to send the user instead, the
 * default app when it is enabled, otherwise the first enabled app. `redirectTo` is undefined
 * when there is nowhere to go (no workspace, or no enabled app).
 */
export const getAppRailRouteAccess = <TKey extends string>(
  enabledApps: readonly TAppRailApp<TKey>[],
  appKey: TKey,
  workspaceSlug: string | undefined
): TAppRailRouteAccess => {
  if (enabledApps.some((app) => app.key === appKey)) return { isAllowed: true };
  const fallbackApp = enabledApps.find((app) => app.isDefault) ?? enabledApps[0];
  return {
    isAllowed: false,
    redirectTo: workspaceSlug && fallbackApp ? fallbackApp.getHref(workspaceSlug) : undefined,
  };
};
