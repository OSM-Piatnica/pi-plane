# App rail

The app rail is the narrow vertical bar on the left edge of a workspace. Each item is an
"app": a part of Pi-Plane with its own routes and its own contextual sidebar. The rail is
built from a registry, so adding an app means registering it rather than editing the shell.

Today the registry holds one app, **Projects**. With a single app there is nothing to switch
between, so the rail is not shown and the shell looks exactly as it did before the registry.

## What the registry drives

| Part                 | With one enabled app | With two or more                                                 |
| -------------------- | -------------------- | ---------------------------------------------------------------- |
| Rail (`AppRailRoot`) | not rendered         | one item per enabled app the user did not hide, in their order   |
| Active item          | (none shown)         | the app that owns the current route                              |
| Command palette      | no extra entries     | "Switch to ..." entry per app, in the Navigation group           |
| Keyboard shortcuts   | none                 | `G` then `1`, `G` then `2`, ... by position in the rail          |
| Shortcuts dialog     | no extra rows        | lists the shortcuts above                                        |
| Docking              | nothing to dock      | "Dock app rail" / "Undock app rail" in the palette               |
| Customise dialog     | no "Apps" section    | order of the apps, hidden apps and the default app               |
| Workspace root       | opens as always      | sends the user to their default or last used app (see "Landing") |
| Last used app        | not recorded         | remembered per workspace in `localStorage`                       |

When the rail is shown it keeps the parts it already had: the right-click menu with "icon only" /
"icon with name" and "undock app rail", the per-workspace docking state in `localStorage`
(`APP_RAIL_<workspaceSlug>`), and the Settings item below the apps. The right-click menu also
opens the customise navigation dialog, so an app without the Projects sidebar has a way to it.

### Docking

An undocked rail is not rendered at all, so its right-click menu, the only place that offered
"dock app rail", disappears with it. To give the way back, the command palette gets a
"Dock app rail" entry (group Miscellaneous) while the rail is undocked, and "Undock app rail"
while it is docked. Like the switch commands, the entry exists only when more than one app is
enabled. It has no keyboard shortcut.

### Routes of a disabled app

An app that is not enabled for a user must not open when its URL is typed or bookmarked. Each
app's layout is wrapped in `<AppRailAppGuard appKey>`: for a disabled app it renders nothing and
replaces the route with the default app's (or, if the default app is itself disabled, the first
enabled app's). The decision is the pure `getAppRailRouteAccess`. Projects, the default app that
is always enabled, is not wrapped. The guard hides the UI only: API endpoints of an app need
their own permission checks.

## Where things live

| File                                                       | Content                                                                                                                    |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `packages/types/src/app-rail.ts`                           | `TAppRailAppKey` (the union of app keys), `TAppRailApp`, `TAppRailContext`                                                 |
| `packages/constants/src/app-rail.ts`                       | reserved route segments, shortcut prefix and limit                                                                         |
| `packages/utils/src/app-rail.ts`                           | pure helpers: enabled apps, active app from a path, rail items, route access, shortcut for a position, registry validation |
| `apps/web/components/app-rail/registry.ts`                 | the app definitions and `APP_RAIL_APPS`, in rail order (no React code)                                                     |
| `apps/web/components/app-rail/registry-icons.ts`           | `APP_RAIL_APP_ICONS`: icon per app                                                                                         |
| `apps/web/components/app-rail/app-sidebar.tsx`             | `APP_RAIL_APP_SIDEBARS` and `<AppRailAppSidebar appKey>` for app layouts                                                   |
| `apps/web/components/app-rail/app-guard.tsx`               | `<AppRailAppGuard appKey>`: keeps a disabled app's routes from rendering                                                   |
| `apps/web/components/app-rail/use-app-rail-apps.ts`        | `useAppRailApps()`: enabled apps, rail apps in the user's order, active app, `hasMultipleApps`                             |
| `apps/web/components/app-rail/app-landing.tsx`             | `<AppRailLanding>`: the landing redirect at the workspace root, and the recording of the last used app                     |
| `apps/web/components/app-rail/last-used-app.ts`            | reads and writes the last used app in `localStorage`                                                                       |
| `apps/web/components/app-rail/app-preferences-section.tsx` | the "Apps" section of the customise navigation dialog                                                                      |
| `apps/api/plane/utils/app_rail.py`                         | the app keys the API accepts for `default_app` and for the `app_rail:<key>` preferences                                    |
| `apps/web/components/app-rail/switch-commands.ts`          | command palette entries and shortcuts, generated from the enabled apps                                                     |
| `apps/web/components/power-k/core/physical-digit.ts`       | lets a sequence ending in a digit complete on layouts with shifted digits                                                  |
| `apps/web/components/app-rail/app-rail-hoc.tsx`            | turns the enabled apps into rail items                                                                                     |
| `apps/web/hooks/app-rail/provider.tsx`                     | enables the rail when more than one app is enabled                                                                         |

Types and constants are in the shared packages, as for other features; the pure helpers are in
`@plane/utils` because that package owns pure logic and has its own tests. Everything that needs
React, the stores or the router stays in `apps/web`.

## An app definition

```ts
type TAppRailApp = {
  key: TAppRailAppKey;
  i18n_label: string; // label under the rail icon
  i18n_switch_label: string; // command palette entry, e.g. "Switch to Projects"
  routeSegments: readonly string[]; // first path segments after the workspace slug
  isDefault?: boolean; // exactly one app; owns every path no app claims
  getHref: (workspaceSlug: string) => string; // where the rail item leads
  isEnabled: (context: TAppRailContext) => boolean;
};
```

`isEnabled` receives `{ workspaceSlug, workspace, user, workspaceRole, features }`. The first four
can be `undefined` while data loads, so a predicate should return `false` until it knows.
`features` is never missing: it holds every workspace feature switch as a boolean, all `false`
until the workspace has loaded.

### An app behind a feature switch

An app that a workspace admin can switch off reads its switch from the context:

```ts
isEnabled: ({ features }) => features.approvals,
// or, combined with a role
isEnabled: ({ features, workspaceRole }) =>
  features.approvals && workspaceRole !== undefined && workspaceRole >= EUserWorkspaceRoles.MEMBER,
```

Nothing else is needed in the shell: while the switch is off the app is not enabled, so it has no
rail item, no command, no shortcut, and `AppRailAppGuard` keeps its routes closed. The switch
itself (the key, making it available, the settings page) is described in
[`workspace-features.md`](./workspace-features.md). The API endpoints of the app must check the
switch on their own (`is_enabled` of the workspace's `WorkspaceFeature` row); the guard hides the
UI only.

The switch label is a full sentence per app, not "Switch to {app}", because the app name has to
be inflected in several languages.

### Which app is active

`getActiveAppRailAppKey(enabledApps, pathname, workspaceSlug)` decides from the first path
segment after the workspace slug:

1. `settings` and `notifications` belong to no app (Settings has its own rail item,
   notifications live in the top bar).
2. A segment listed in an enabled app's `routeSegments` belongs to that app.
3. Everything else belongs to the default app (Projects). This includes the compact
   `/i/:workItem` link, which renders in the workspace shell without the slug in the URL.

Segments are compared whole: `/acme/approvals-archive` is not the `approvals` app.

## Adding an app

The example adds an **Approvals** app at `/:workspaceSlug/approvals`.

1. **Key.** Add it to the union in `packages/types/src/app-rail.ts`:

   ```ts
   export type TAppRailAppKey = "projects" | "approvals";
   ```

   From here the type check fails until the app has a definition (step 3) and an icon (step 4):
   both are records over this union. The sidebar map is partial on purpose (an app may have no
   sidebar), and nothing checks the route group, the routes or the guard: steps 5 to 8 are on you.

   Add the same key to `APP_RAIL_APP_KEYS` in `apps/api/plane/utils/app_rail.py`. The API accepts
   only these keys as a user's default app and in the `app_rail:<key>` preferences, and
   `apps/web/tests/unit/app-preferences-and-features.test.ts` fails while the two lists differ.

2. **Strings.** Add the rail label and the switch label to
   `packages/i18n/src/locales/en/pi-extensions.json`, then to every locale (follow the
   `translate` skill and run `pnpm --filter @plane/i18n run sync:check`):

   ```json
   "app_rail": {
     "apps": { "approvals": "Approvals" },
     "switch_to": { "approvals": "Switch to Approvals", "projects": "Switch to Projects" }
   }
   ```

3. **Registration.** Add the app to `APP_RAIL_APP_DEFINITIONS` in
   `apps/web/components/app-rail/registry.ts`. The position of the entry is the position in the
   rail and decides the shortcut (`G` `2` for the second app):

   ```ts
   approvals: {
     key: "approvals",
     i18n_label: "app_rail.apps.approvals",
     i18n_switch_label: "app_rail.switch_to.approvals",
     routeSegments: ["approvals"],
     getHref: (workspaceSlug) => `/${workspaceSlug}/approvals/`,
     isEnabled: ({ workspaceRole }) => workspaceRole !== undefined && workspaceRole >= EUserWorkspaceRoles.MEMBER,
   },
   ```

4. **Icon.** Add it to `APP_RAIL_APP_ICONS` in `registry-icons.ts` (an icon from
   `@makeplane/propel/icons`).

5. **Route group.** Create the app's folder next to `(projects)`:

   ```
   apps/web/app/(all)/[workspaceSlug]/(approvals)/
     layout.tsx        the app's frame: guard, power-k provider, sidebar, <Outlet />
     _sidebar.tsx      the contextual sidebar (optional)
     approvals/page.tsx
   ```

   The layout mirrors `(projects)/layout.tsx`. Mount `ProjectsAppPowerKProvider` in it so the
   command palette and the app switching shortcuts work inside the app, and render the sidebar
   through the registry.

6. **Guard.** Wrap the whole layout in `<AppRailAppGuard appKey>`, so the routes do not render
   for a user whose `isEnabled` says no (see "Routes of a disabled app"):

   ```tsx
   export default function ApprovalsLayout() {
     return (
       <AppRailAppGuard appKey="approvals">
         <ProjectsAppPowerKProvider />
         <div className="relative flex h-full w-full flex-col overflow-hidden rounded-lg border border-subtle">
           <div className="relative flex size-full overflow-hidden">
             <AppRailAppSidebar appKey="approvals" />
             <main className="relative flex h-full w-full flex-col overflow-hidden bg-surface-1">
               <Outlet />
             </main>
           </div>
         </div>
       </AppRailAppGuard>
     );
   }
   ```

7. **Sidebar.** If the app has one, add it to `APP_RAIL_APP_SIDEBARS` in `app-sidebar.tsx`.
   Only app layouts may import that module (see the comment in the file).

8. **Routes.** Register the route group in `apps/web/app/routes/extended.ts`, inside the
   workspace layout and next to the `(projects)` entry:

   ```ts
   layout("./(all)/[workspaceSlug]/(approvals)/layout.tsx", [
     route(":workspaceSlug/approvals", "./(all)/[workspaceSlug]/(approvals)/approvals/page.tsx"),
   ]),
   ```

9. **Tests.** `apps/web/tests/unit/app-rail-registry.test.ts` validates the registry (one default
   app, no duplicate keys, no route segment claimed twice or reserved, labels present in the
   English locale). Update its "offers Projects alone" case, which pins the single-app state.

Nothing in the shell needs to change: once a second app is enabled for a user, the rail, the
active state, the command palette entries, the shortcuts, the "Apps" section of the customise
dialog and the landing appear for that user.

## A user's preferences

All of this exists only for a user with more than one enabled app. It was built before a second
app existed, so so far it has run only in unit and contract tests.

### Order and hidden apps

The customise navigation dialog (the button in the Projects sidebar, or the rail's right-click
menu) gets an "Apps" section: drag to reorder, untick to hide. The last app left in the rail
cannot be unticked.

The state is stored with the other sidebar preferences, in `WorkspaceUserPreference`
(`/api/workspaces/:slug/sidebar-preferences/`), one row per app:

| Field        | Meaning for an app                                |
| ------------ | ------------------------------------------------- |
| `key`        | `app_rail:<app key>`, for example `app_rail:wiki` |
| `sort_order` | position in the rail, ascending                   |
| `is_pinned`  | `false` hides the app from the rail               |

- A row is created the first time the user changes something (the endpoint creates rows only for
  keys of known apps). Without a row an app is shown, after the apps that have one, in registry
  order. So an app registered later appears at the end of a customised rail.
- Hidden is not disabled. A hidden app keeps its routes and its command palette entry; the
  shortcuts `G` `1`, `G` `2`, ... follow the rail, and hidden apps are numbered after the rail apps.
- If every app is hidden (stale data), nothing is hidden.

The pure logic is `arrangeAppRailApps` in `packages/utils/src/app-rail.ts`.

### Default app and landing

`default_app` is the key of the app a user wants to land in. It lives on the user's
`WorkspaceUserProperties` row of the workspace (`/api/workspaces/:slug/user-properties/`, which
the web app already loads), is `null` by default, and the API rejects a key that is not in
`APP_RAIL_APP_KEYS`. The user sets it in the same "Apps" section: "Last used app" (no default) or
one of their enabled apps.

When a user enters a workspace, `<AppRailLanding>` (in the workspace layout) decides where they
go. The order is:

1. **An explicit deep link.** Any path other than the workspace root is opened as it is.
2. **The default app**, when one is set and it is enabled for the user.
3. **The last used app** in this workspace, when it is still enabled. It is kept in
   `localStorage` (`APP_RAIL_LAST_APP_<workspaceSlug>`), so it is per device, and a blocked or
   full storage just means nothing is remembered.
4. **The workspace root as before**: the home of the Projects app.

Details:

- "Entering" happens once per page load and workspace: opening the app, coming back from sign-in
  (the sign-in flow ends at `/:workspaceSlug/` unless it carries a `next_path`, which is a deep
  link), and switching workspaces. Going to the root later, for example with the Projects rail
  item, is not a new entry and is not redirected.
- The root stays blank for a moment while the user's properties load, so the Projects home does
  not flash before the redirect. If they do not load within three seconds the root opens as
  before. With a single app, and on any deep link, nothing waits.
- A default app that was switched off for the user later is skipped (step 3 applies) and shown
  as "Last used app" in the dialog; the stored key is left alone.
- If the app that owns the root is not enabled for a user, they land in their first enabled app
  instead of on a page they cannot use.

The pure logic is `getAppRailLandingApp`, `getAppRailLandingRedirect` and `resolveAppRailLanding`.

Note the two meanings of "default": `isDefault` in an app definition marks the app that owns
every path no other app claims (Projects); `default_app` is a user's choice of where to land.

### Not built yet

- **Default app per role** (for example guests land in Lite; roadmap E4). It fits between steps 2
  and 3: pass the workspace's default for the user's role to `getAppRailLandingApp` as a further
  candidate. The workspace side can be a `WorkspaceFeature`-like row or a field; nothing here
  assumes where it is stored.
- **A workspace admin setting another member's default app** (E4). `default_app` is on the row
  keyed by workspace and user, so an admin endpoint can write it for any member without touching
  `WorkspaceMember` or the member list payload.
- **Restricting a role to some apps** (`allowed_apps`, later). That is an `isEnabled` concern: the
  landing already handles a user whose root app is not enabled.

## Keyboard shortcuts

App switching uses the key sequence `G` + digit, by position in the rail, for the first nine
apps. `G` is already the "go to" prefix of the command palette (`G` `H` home, `G` `P` projects
list, ...), and no existing sequence uses a digit, so:

- no existing sequence collides with or is a prefix of the new ones;
- no new prefix key is introduced. A prefix key swallows the single-key shortcut on the same
  key (`ShortcutHandler` waits for the rest of the sequence), which is why a fresh letter such as
  `A` (assign) was not used.

Browser-level combinations (`Ctrl`/`Cmd` + digit, `Alt` + digit) were avoided because browsers
use them to switch tabs. The unit test scans the command palette sources and fails if a later
binding collides with `g1` to `g9`.

### Layouts with shifted digits

On French AZERTY, Czech and Slovak layouts the digit row types other characters (`&é"'`, `+ěšč`)
and digits need `Shift`, which cancels a pending sequence. So after a sequence prefix the handler
also accepts the digit key by its physical position (`KeyboardEvent.code` `Digit1` to `Digit9`):
`G` then the key that carries `1` works on every layout, with or without the layout map that
only Chromium exposes. This is `resolveSequenceKey` in `components/power-k/core/physical-digit.ts`.
It applies only when a sequence is pending, the typed character neither completes nor continues
any sequence, and the digit completes one, so single-key shortcuts and existing sequences behave
as before. The numeric keypad works as well, because it types digits directly.
