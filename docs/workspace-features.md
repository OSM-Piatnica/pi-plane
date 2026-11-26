# Workspace feature switches

A workspace admin can switch whole parts of Pi-Plane on or off for a workspace. The known
switches are:

| Key           | For                              | Available |
| ------------- | -------------------------------- | --------- |
| `lite`        | the "My tasks" app (roadmap E)   | no        |
| `approvals`   | the Approvals app (roadmap C6)   | no        |
| `initiatives` | the Initiatives app (roadmap F2) | no        |
| `wiki`        | the workspace wiki (roadmap G4)  | no        |
| `raci`        | RACI on work items (roadmap D2)  | yes       |

"Available" means the feature is built. Only `raci` is (see [`raci.md`](./raci.md)), so the settings page
"Features" is listed for workspace admins and offers that one switch.

## How it works

- **Storage.** `WorkspaceFeature` (`workspace`, `key`, `is_enabled`; one row per workspace and
  key, table `workspace_features`). No row means off, so every switch is off by default. The key
  is a plain string and not a choice field: adding a key needs no migration. A table was chosen
  over boolean fields on `Workspace` for that reason, and to keep the fork's changes out of a
  model that upstream edits.
- **The list of keys** is kept twice, and a unit test of the web app
  (`apps/web/tests/unit/app-preferences-and-features.test.ts`) fails when the two differ:
  - API: `WORKSPACE_FEATURES` in `apps/api/plane/utils/workspace_features.py` (key to available);
  - web: `WORKSPACE_FEATURES` in `packages/constants/src/workspace-features.ts`, keys typed by
    `TWorkspaceFeatureKey` in `packages/types/src/workspace-features.ts`.
- **Reading.** The enabled keys travel with the workspace: `enabled_features` (a list of keys) in
  the workspace payload the web app already loads (`/api/users/me/workspaces/`), so every member,
  guests included, has them as soon as the workspace is known, without a further request. Only
  keys that are both available and switched on are listed.
- **Writing.** `PATCH /api/workspaces/:slug/features/` with `{ "<key>": true | false }`, workspace
  admins only. An unknown key, a key that is not available, or a value that is not a boolean is
  rejected with 400 and nothing is saved. `GET` on the same address returns `{ key: is_enabled }`
  for every available feature and is open to every member.
- **Web.** `useWorkspaceFeatures()` (`apps/web/hooks/use-workspace-features.ts`) gives
  `features` (every key as a boolean), `isFeatureEnabled(key)`, `availableFeatures` and
  `updateFeature`. The app rail hands the same flags to each app's `isEnabled` (see
  [`app-rail.md`](./app-rail.md), "An app behind a feature switch").
- **Settings page.** Workspace settings, "Features" (`/:workspaceSlug/settings/features`), for
  workspace admins: one row per available feature with its name, a one-line description and a
  switch. While no feature is available the page is not in the sidebar or the command palette
  (`isWorkspaceSettingsItemAvailable`), and its address leads back to the general settings.

## Making a feature available

When the feature behind a key is built:

1. API: set the key to `True` in `WORKSPACE_FEATURES` (`apps/api/plane/utils/workspace_features.py`).
2. Web: in `packages/constants/src/workspace-features.ts` set `isAvailable: true` and give the
   feature its strings. The type requires them from this moment:

   ```ts
   approvals: {
     key: "approvals",
     isAvailable: true,
     i18n_title: "workspace_features.items.approvals.title",
     i18n_description: "workspace_features.items.approvals.description",
   },
   ```

3. Strings: add the title and the one-line description to
   `packages/i18n/src/locales/en/pi-extensions.json`, then to every locale (follow the
   `translate` skill and run `pnpm --filter @plane/i18n run sync:check`).
4. Use the switch:
   - a rail app: `isEnabled: ({ features }) => features.approvals` in its registry entry;
   - anything else in the web app: `useWorkspaceFeatures().isFeatureEnabled("approvals")`;
   - the API: the feature's endpoints check the switch themselves, for example with
     `enabled_workspace_feature_keys(workspace)`. Hiding the UI is not access control.
5. Tests: `WORKSPACE_FEATURES as shipped` in `packages/utils/tests/workspace-features.spec.ts` and
   `TestWorkspaceFeaturesAsShipped` in
   `apps/api/plane/tests/contract/app/test_workspace_features_app.py` pin which features are available;
   update them.

A feature that is switched on by default for existing workspaces needs a data migration that
creates the rows; the default of a missing row stays "off".

## Adding a key

Add it to `TWorkspaceFeatureKey`, to both `WORKSPACE_FEATURES` lists (not available), and to the
table above. No migration is needed.

## Performance note

`enabled_features` is computed per workspace from `workspace.workspace_features.all()`, and not at
all while no feature is available. The workspace list endpoint serializes all workspaces of a
user; when the first feature becomes available, add `prefetch_related("workspace_features")` to
`UserWorkSpacesEndpoint` so the list stays at one query for the switches.
