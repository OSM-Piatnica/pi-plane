# App rail

The app rail is the narrow vertical bar on the left edge of a workspace. Each item is an
"app": a part of Pi-Plane with its own routes and its own contextual sidebar. The rail is
built from a registry, so adding an app means registering it rather than editing the shell.

Today the registry holds one app, **Projects**. With a single app there is nothing to switch
between, so the rail is not shown and the shell looks exactly as it did before the registry.

## What the registry drives

| Part                 | With one enabled app | With two or more                                        |
| -------------------- | -------------------- | ------------------------------------------------------- |
| Rail (`AppRailRoot`) | not rendered         | one item per enabled app, in registry order             |
| Active item          | (none shown)         | the app that owns the current route                     |
| Command palette      | no extra entries     | "Switch to ..." entry per app, in the Navigation group  |
| Keyboard shortcuts   | none                 | `G` then `1`, `G` then `2`, ... by position in the rail |
| Shortcuts dialog     | no extra rows        | lists the shortcuts above                               |

When the rail is shown, its existing behaviour applies unchanged: the right-click menu with
"icon only" / "icon with name" and "undock app rail", the per-workspace docking state in
`localStorage` (`APP_RAIL_<workspaceSlug>`), and the Settings item below the apps.

## Where things live

| File                                                | Content                                                                                               |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `packages/types/src/app-rail.ts`                    | `TAppRailAppKey` (the union of app keys), `TAppRailApp`, `TAppRailContext`                            |
| `packages/constants/src/app-rail.ts`                | reserved route segments, shortcut prefix and limit                                                    |
| `packages/utils/src/app-rail.ts`                    | pure helpers: enabled filtering, active app from a path, shortcut for a position, registry validation |
| `apps/web/components/app-rail/registry.ts`          | `APP_RAIL_APPS`: the apps, in rail order (no React code)                                              |
| `apps/web/components/app-rail/registry-icons.ts`    | `APP_RAIL_APP_ICONS`: icon per app                                                                    |
| `apps/web/components/app-rail/app-sidebar.tsx`      | `APP_RAIL_APP_SIDEBARS` and `<AppRailAppSidebar appKey>` for app layouts                              |
| `apps/web/components/app-rail/use-app-rail-apps.ts` | `useAppRailApps()`: enabled apps, active app, `hasMultipleApps`                                       |
| `apps/web/components/app-rail/switch-commands.ts`   | command palette entries and shortcuts, generated from the enabled apps                                |
| `apps/web/components/app-rail/app-rail-hoc.tsx`     | turns the enabled apps into rail items                                                                |
| `apps/web/hooks/app-rail/provider.tsx`              | enables the rail when more than one app is enabled                                                    |

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

`isEnabled` receives `{ workspaceSlug, workspace, user, workspaceRole }`. Any field can be
`undefined` while data loads, so a predicate should return `false` until it knows. Workspace
feature switches (roadmap G3) will be added to this context.

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

   From here the compiler reports the missing icon.

2. **Strings.** Add the rail label and the switch label to
   `packages/i18n/src/locales/en/pi-extensions.json`, then to every locale (follow the
   `translate` skill and run `pnpm --filter @plane/i18n run sync:check`):

   ```json
   "app_rail": {
     "apps": { "approvals": "Approvals" },
     "switch_to": { "approvals": "Switch to Approvals", "projects": "Switch to Projects" }
   }
   ```

3. **Registration.** Add the app to `APP_RAIL_APPS` in
   `apps/web/components/app-rail/registry.ts`. The position in the array is the position in the
   rail and decides the shortcut (`G` `2` for the second app):

   ```ts
   {
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
     layout.tsx        the app's frame: power-k provider, sidebar, <Outlet />
     _sidebar.tsx      the contextual sidebar (optional)
     approvals/page.tsx
   ```

   The layout mirrors `(projects)/layout.tsx`. Mount `ProjectsAppPowerKProvider` in it so the
   command palette and the app switching shortcuts work inside the app, and render the sidebar
   through the registry:

   ```tsx
   export default function ApprovalsLayout() {
     return (
       <>
         <ProjectsAppPowerKProvider />
         <div className="relative flex h-full w-full flex-col overflow-hidden rounded-lg border border-subtle">
           <div className="relative flex size-full overflow-hidden">
             <AppRailAppSidebar appKey="approvals" />
             <main className="relative flex h-full w-full flex-col overflow-hidden bg-surface-1">
               <Outlet />
             </main>
           </div>
         </div>
       </>
     );
   }
   ```

6. **Sidebar.** If the app has one, add it to `APP_RAIL_APP_SIDEBARS` in `app-sidebar.tsx`.
   Only app layouts may import that module (see the comment in the file).

7. **Routes.** Register the route group in `apps/web/app/routes/extended.ts`, inside the
   workspace layout and next to the `(projects)` entry:

   ```ts
   layout("./(all)/[workspaceSlug]/(approvals)/layout.tsx", [
     route(":workspaceSlug/approvals", "./(all)/[workspaceSlug]/(approvals)/approvals/page.tsx"),
   ]),
   ```

8. **Tests.** `apps/web/tests/unit/app-rail-registry.test.ts` validates the registry (one default
   app, no duplicate keys, no route segment claimed twice or reserved, labels present in the
   English locale). Update its "offers Projects alone" case, which pins the single-app state.

Nothing in the shell needs to change: once a second app is enabled for a user, the rail, the
active state, the command palette entries and the shortcuts appear for that user.

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

Limitation: on layouts where digits need `Shift` (for example French AZERTY) the sequence does
not fire, as for any shortcut bound to a digit; the command palette entry still works.

## Not part of the registry yet

- Default app, last used app, order and hidden apps per user: roadmap G2.
- Workspace feature switches read by `isEnabled`: roadmap G3.
