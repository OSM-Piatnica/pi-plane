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
