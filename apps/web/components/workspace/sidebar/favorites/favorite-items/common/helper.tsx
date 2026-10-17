/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { LucideIcon } from "lucide-react";
import { Logo } from "@plane/propel/emoji-icon-picker";
import type { ISvgIcons } from "@plane/propel/icons";
import { CyclesOutline, ModuleOutline, PagesOutline, ProjectsOutline, ViewsOutline } from "@makeplane/propel/icons";
import { FavoriteFolderIcon } from "@plane/propel/icons";
// plane imports
import type { IFavorite, TLogoProps } from "@plane/types";
import { FAVORITE_ITEM_LINKS } from "@plane/constants";

const FAVORITE_ITEM_ICONS: Record<string, React.FC<ISvgIcons> | LucideIcon> = {
  page: PagesOutline,
  project: ProjectsOutline,
  view: ViewsOutline,
  module: ModuleOutline,
  cycle: CyclesOutline,
  folder: FavoriteFolderIcon,
};

export const getFavoriteItemIcon = (type: string, logo?: TLogoProps) => {
  const Icon = FAVORITE_ITEM_ICONS[type] || PagesOutline;

  return (
    <>
      <div className="hidden size-5 items-center justify-center group-hover:flex">
        <Icon className="m-auto size-4 flex-shrink-0 stroke-[1.5]" />
      </div>
      <div className="flex size-5 items-center justify-center group-hover:hidden">
        {logo?.in_use ? (
          <Logo logo={logo} size={16} type={type === "project" ? "material" : "lucide"} />
        ) : (
          <Icon className="m-auto size-4 flex-shrink-0 stroke-[1.5]" />
        )}
      </div>
    </>
  );
};

export const generateFavoriteItemLink = (workspaceSlug: string, favorite: IFavorite) => {
  const entityLinkDetails = FAVORITE_ITEM_LINKS[favorite.entity_type];

  if (!entityLinkDetails) {
    console.error(`Unrecognized favorite entity type: ${favorite.entity_type}`);
    return `/${workspaceSlug}`;
  }

  if (entityLinkDetails.itemLevel === "workspace") {
    return `/${workspaceSlug}/${entityLinkDetails.getLink(favorite)}`;
  } else if (entityLinkDetails.itemLevel === "project") {
    return `/${workspaceSlug}/projects/${favorite.project_id}/${entityLinkDetails.getLink(favorite)}`;
  } else {
    return `/${workspaceSlug}`;
  }
};
