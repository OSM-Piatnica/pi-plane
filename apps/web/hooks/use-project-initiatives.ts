/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import useSWR from "swr";
import { canReadInitiatives } from "@/helpers/initiatives";
import { useInitiative } from "@/hooks/store/use-initiative";
import { useUserPermissions } from "@/hooks/store/user";
import { useWorkspaceFeatures } from "@/hooks/use-workspace-features";

/**
 * The initiatives for the project list and the project header (roadmap F3). `isEnabled` is true while the
 * Initiatives feature is on and the person may read initiatives (a workspace admin or member); the list of the
 * workspace is then loaded once, shared with the Initiatives app. Call it from an `observer` component.
 */
export const useProjectInitiatives = () => {
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const { isFeatureEnabled } = useWorkspaceFeatures();
  const { getWorkspaceRoleByWorkspaceSlug } = useUserPermissions();
  const initiativeStore = useInitiative();
  const isEnabled =
    !!slug && isFeatureEnabled("initiatives") && canReadInitiatives(getWorkspaceRoleByWorkspaceSlug(slug));

  useSWR(
    isEnabled && slug ? `WORKSPACE_INITIATIVES_${slug}` : null,
    slug ? () => initiativeStore.fetchInitiatives(slug) : null,
    { revalidateOnFocus: false }
  );

  return {
    isEnabled,
    isLoaded: isEnabled && initiativeStore.isListLoaded && initiativeStore.workspaceSlug === slug,
    tree: initiativeStore.tree,
    getInitiativeById: initiativeStore.getInitiativeById,
  };
};
