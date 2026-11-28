/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { layout, route } from "@react-router/dev/routes";
import type { RouteConfigEntry } from "@react-router/dev/routes";

export const extendedRoutes: RouteConfigEntry[] = [
  layout("./(all)/layout.tsx", [
    layout("./(all)/[workspaceSlug]/layout.tsx", [
      layout("./(all)/[workspaceSlug]/(projects)/layout.tsx", [
        layout("./(all)/[workspaceSlug]/(projects)/browse/[workItem]/layout.tsx", [
          // Compact work item link of the instance's default workspace (see `app/compat/next/route-policy-context`)
          route("i/:workItem", "./(all)/short-work-item/page.tsx"),
        ]),
      ]),
      // The Initiatives rail app (`docs/initiatives.md`, `docs/app-rail.md`)
      layout("./(all)/[workspaceSlug]/(initiatives)/layout.tsx", [
        route(":workspaceSlug/initiatives", "./(all)/[workspaceSlug]/(initiatives)/initiatives/page.tsx"),
        route(
          ":workspaceSlug/initiatives/:initiativeId",
          "./(all)/[workspaceSlug]/(initiatives)/initiatives/[initiativeId]/page.tsx"
        ),
      ]),
    ]),
  ]),
];
