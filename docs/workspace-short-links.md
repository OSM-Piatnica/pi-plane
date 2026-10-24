<!--
Copyright (c) 2026-present Maciej Szymczak and contributors
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
Adapted from the default workspace short links of Hangar (szymczag/hangar, AGPL-3.0-only).
See the LICENSE file for details.
-->

# Default workspace short links

Pi-Plane can give one workspace compact work item addresses such as `/i/AA-123`.
Choose that workspace in **God Mode → Workspaces** with **Use for short links**.
Select **Short links enabled** again to clear the choice.

The setting is the instance configuration key `INSTANCE_DEFAULT_WORKSPACE_ID`
(seeded from the environment variable of the same name, empty by default). Only
an instance admin can change it, and the API refuses a value that is not the
UUID of an existing workspace.

The stored value is the workspace UUID, not its slug, so renaming the workspace
does not break compact links. The public instance configuration
(`default_workspace_id`) only reports the UUID while that workspace still
exists; a missing or invalid value disables compact routing safely.

Only canonical work item browse routes are shortened:

- `/workspace-name/browse/AA-123` becomes `/i/AA-123` for the selected workspace.
- Project, settings, archive and all non-selected workspace routes keep their
  workspace slug.

The web app resolves `/i/:workItem` to the selected workspace for the existing
authenticated layouts, stores and authorization wrappers, and normalizes links
and imperative navigation to the compact form. A work item opened by its
workspace-qualified address is shown under the compact one once the
configuration has loaded. The compact link is not an HTTP redirect to the
workspace-qualified address.

If the setting is absent, stale, or points to a workspace the signed-in user
cannot access, the existing authorization flow refuses the request without
revealing workspace contents.
