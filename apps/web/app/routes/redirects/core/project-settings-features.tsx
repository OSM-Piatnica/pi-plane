/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { redirect } from "react-router";
import type { Route } from "./+types/project-settings-features";

// The features used to have a settings page each (/features/cycles, /features/modules, ...); they share one page now.
export const clientLoader = ({ params }: Route.ClientLoaderArgs) => {
  const { workspaceSlug, projectId } = params;
  throw redirect(`/${workspaceSlug}/settings/projects/${projectId}/features/`);
};

export default function ProjectSettingsFeatures() {
  return null;
}
