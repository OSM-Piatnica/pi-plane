/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import {
  APP_RAIL_MAX_SWITCH_SHORTCUTS,
  APP_RAIL_NON_APP_ROUTE_SEGMENTS,
  APP_RAIL_PREFERENCE_KEY_PREFIX,
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

/**
 * A user's stored order and hidden state of the rail apps: the workspace's sidebar preferences
 * (`WorkspaceUserPreference`), of which only the `app_rail:<key>` entries are read here.
 */
export type TAppRailAppPreferences = Readonly<Record<string, { is_pinned?: boolean; sort_order?: number } | undefined>>;

/** Key of a rail app in the workspace's sidebar preferences */
export const getAppRailPreferenceKey = (appKey: string): string => `${APP_RAIL_PREFERENCE_KEY_PREFIX}${appKey}`;

export type TAppRailArrangement<TKey extends string> = {
  /** Every enabled app in the user's order, with its hidden state: the rows of the customise dialog */
  items: { app: TAppRailApp<TKey>; isHidden: boolean }[];
  /** The apps shown in the rail, in the user's order */
  railApps: TAppRailApp<TKey>[];
  /** The rail apps followed by the hidden ones: the order of the switch commands and shortcuts */
  orderedApps: TAppRailApp<TKey>[];
};

/**
 * Applies a user's preferences to the enabled apps.
 *
 * - Order: apps with a stored `sort_order` come first, ascending; apps without one (never
 *   reordered, or registered later) follow in registry order.
 * - Hidden: an app whose preference says `is_pinned: false` leaves the rail. It stays enabled:
 *   its routes open, and it keeps its command palette entry.
 * - Hiding every app would leave an empty rail, so then nothing is hidden. This also means a
 *   single enabled app can never be hidden.
 */
export const arrangeAppRailApps = <TKey extends string>(
  enabledApps: readonly TAppRailApp<TKey>[],
  preferences?: TAppRailAppPreferences | null
): TAppRailArrangement<TKey> => {
  const rows = enabledApps.map((app, index) => {
    const preference = preferences?.[getAppRailPreferenceKey(app.key)];
    const sortOrder = preference?.sort_order;
    return {
      app,
      index,
      sortOrder: typeof sortOrder === "number" && Number.isFinite(sortOrder) ? sortOrder : undefined,
      isHidden: preference?.is_pinned === false,
    };
  });
  const sorted = rows.toSorted((a, b) => {
    if (a.sortOrder !== undefined && b.sortOrder !== undefined) return a.sortOrder - b.sortOrder || a.index - b.index;
    if (a.sortOrder !== undefined) return -1;
    if (b.sortOrder !== undefined) return 1;
    return a.index - b.index;
  });
  const isEveryAppHidden = sorted.every((row) => row.isHidden);
  const items = sorted.map((row) => ({ app: row.app, isHidden: row.isHidden && !isEveryAppHidden }));
  const railApps = items.filter((item) => !item.isHidden).map((item) => item.app);
  const hiddenApps = items.filter((item) => item.isHidden).map((item) => item.app);
  return { items, railApps, orderedApps: [...railApps, ...hiddenApps] };
};

export type TAppRailState<TKey extends string> = {
  /** Apps offered in this context, in registry order */
  enabledApps: TAppRailApp<TKey>[];
  /** The enabled apps the user did not hide, in the user's order: the items of the rail */
  railApps: TAppRailApp<TKey>[];
  /** The rail apps followed by the hidden ones: the order of the switch commands and shortcuts */
  orderedApps: TAppRailApp<TKey>[];
  /** The enabled app the current route belongs to */
  activeAppKey: TKey | undefined;
  /** False with a single enabled app: no rail, no switch commands, no shortcuts */
  hasMultipleApps: boolean;
};

/**
 * Everything the shell derives from the registry for one workspace, user and route.
 * `preferences` are the user's sidebar preferences of the workspace; without them the rail is
 * in registry order with nothing hidden.
 */
export const getAppRailState = <TKey extends string>(
  apps: readonly TAppRailApp<TKey>[],
  context: TAppRailContext,
  pathname: string,
  preferences?: TAppRailAppPreferences | null
): TAppRailState<TKey> => {
  const enabledApps = getEnabledAppRailApps(apps, context);
  const { railApps, orderedApps } = arrangeAppRailApps(enabledApps, preferences);
  return {
    enabledApps,
    railApps,
    orderedApps,
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

/** The rail items of the apps the user did not hide, in rail order, without their React parts */
export const getAppRailDockItems = <TKey extends string>(
  state: Pick<TAppRailState<TKey>, "railApps" | "activeAppKey">,
  workspaceSlug: string
): TAppRailDockItem<TKey>[] =>
  state.railApps.map((app) => ({
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

/** Whether the path is the workspace root (`/:workspaceSlug/`), where a user lands without a deep link */
export const isWorkspaceRootPath = (pathname: string, workspaceSlug: string | undefined): boolean =>
  Boolean(workspaceSlug) && getWorkspacePathSegments(pathname, workspaceSlug as string)?.length === 0;

/**
 * The app a user should land in when entering a workspace without a deep link:
 *
 * 1. their default app (`default_app` of their workspace properties), when it is enabled for them;
 * 2. else the app they last used in this workspace, when it is still enabled;
 * 3. else nothing: the workspace root renders as it always did (the home of the default app).
 *
 * One exception keeps a restricted user from landing in an app they cannot use: when the app
 * that owns the workspace root is not enabled, the first enabled app is the landing app.
 */
export const getAppRailLandingApp = <TKey extends string>(
  enabledApps: readonly TAppRailApp<TKey>[],
  defaultAppKey: string | null | undefined,
  lastUsedAppKey: string | null | undefined
): TAppRailApp<TKey> | undefined => {
  const preferred =
    (defaultAppKey ? enabledApps.find((app) => app.key === defaultAppKey) : undefined) ??
    (lastUsedAppKey ? enabledApps.find((app) => app.key === lastUsedAppKey) : undefined);
  if (preferred) return preferred;
  return enabledApps.some((app) => app.isDefault) ? undefined : enabledApps[0];
};

export type TAppRailLandingInput<TKey extends string> = {
  enabledApps: readonly TAppRailApp<TKey>[];
  /** The path the user entered the workspace on */
  pathname: string;
  workspaceSlug: string | undefined;
  /** `default_app` of the user's workspace properties */
  defaultAppKey: string | null | undefined;
  /** The app remembered on this device for this workspace */
  lastUsedAppKey: string | null | undefined;
};

/**
 * Where to send a user who has just entered a workspace, or undefined to leave them where they
 * are. The order is: explicit deep link, default app, last used app, the workspace root as before.
 *
 * - Any path other than the workspace root is a deep link and is never redirected.
 * - A landing app whose own address is the workspace root needs no redirect.
 */
export const getAppRailLandingRedirect = <TKey extends string>({
  enabledApps,
  pathname,
  workspaceSlug,
  defaultAppKey,
  lastUsedAppKey,
}: TAppRailLandingInput<TKey>): string | undefined => {
  if (!workspaceSlug || !isWorkspaceRootPath(pathname, workspaceSlug)) return undefined;
  const landingApp = getAppRailLandingApp(enabledApps, defaultAppKey, lastUsedAppKey);
  if (!landingApp) return undefined;
  const href = landingApp.getHref(workspaceSlug);
  return isWorkspaceRootPath(href, workspaceSlug) ? undefined : href;
};

/**
 * The value of the "default app" control: the stored key when it names an enabled app, else
 * undefined ("no default"). A key of an app that was switched off later reads as no default.
 */
export const getAppRailDefaultAppKey = <TKey extends string>(
  enabledApps: readonly TAppRailApp<TKey>[],
  defaultAppKey: string | null | undefined
): TKey | undefined => enabledApps.find((app) => app.key === defaultAppKey)?.key;

export type TAppRailLandingStep =
  /** The user's default app is not known yet: render nothing at the workspace root and wait */
  | { isPending: true }
  /** Decided: go to `redirectTo`, or stay when it is undefined */
  | { isPending: false; redirectTo: string | undefined };

/**
 * One step of the landing decision, taken when a user enters a workspace. It only waits when the
 * answer can depend on the default app: at the workspace root, with more than one enabled app,
 * while the user's workspace properties are still loading. A deep link and a single-app workspace
 * are decided at once, so nothing changes for them.
 */
export const resolveAppRailLanding = <TKey extends string>(
  input: TAppRailLandingInput<TKey> & {
    /** False while the user's workspace properties (and so `defaultAppKey`) have not loaded */
    isDefaultAppKnown: boolean;
  }
): TAppRailLandingStep => {
  const { isDefaultAppKnown, ...landing } = input;
  const isAtRoot = isWorkspaceRootPath(landing.pathname, landing.workspaceSlug);
  if (isAtRoot && hasMultipleAppRailApps(landing.enabledApps) && !isDefaultAppKnown) return { isPending: true };
  return { isPending: false, redirectTo: getAppRailLandingRedirect(landing) };
};

/**
 * The sidebar preference rows that store an arrangement of the rail: one row per app, with its
 * position as `sort_order`. Every row is written each time, so the order the user sees is the
 * order that is kept, also for apps that had no row yet.
 */
export const buildAppRailPreferenceUpdate = (
  items: readonly { app: { key: string }; isHidden: boolean }[]
): { key: string; is_pinned: boolean; sort_order: number }[] =>
  items.map((item, index) => ({
    key: getAppRailPreferenceKey(item.app.key),
    is_pinned: !item.isHidden,
    sort_order: index,
  }));

/**
 * Whether the user may hide this app in the customise dialog: the last app left in the rail
 * cannot be hidden.
 */
export const canHideAppRailApp = (
  items: readonly { app: { key: string }; isHidden: boolean }[],
  appKey: string
): boolean => items.some((item) => !item.isHidden && item.app.key !== appKey);
