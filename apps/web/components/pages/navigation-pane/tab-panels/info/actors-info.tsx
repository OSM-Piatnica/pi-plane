/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
// plane imports
import { Avatar } from "@makeplane/propel/components/avatar";
import { useTranslation } from "@plane/i18n";
import { getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useLocalizedDates } from "@/hooks/use-localized-dates";
// store
import type { TPageInstance } from "@/store/pages/base-page";

type Props = {
  page: TPageInstance;
};

export const PageNavigationPaneInfoTabActorsInfo = observer(function PageNavigationPaneInfoTabActorsInfo(props: Props) {
  const { formatDate, timeAgo } = useLocalizedDates();
  const { page } = props;
  // navigation
  const { workspaceSlug } = useParams();
  // store hooks
  const { getUserDetails } = useMember();
  // derived values
  const { owned_by, updated_by } = page;
  const editorInformation = updated_by ? getUserDetails(updated_by) : undefined;
  const creatorInformation = owned_by ? getUserDetails(owned_by) : undefined;
  // translation
  const { t } = useTranslation();

  return (
    <div className="mt-4 space-y-3">
      <div>
        <p className="text-11 font-medium text-tertiary">{t("page_navigation_pane.tabs.info.actors_info.edited_by")}</p>
        <div className="mt-2 flex items-center justify-between gap-2 text-13 font-medium">
          <Link href={`/${workspaceSlug?.toString()}/profile/${page.updated_by}`} className="flex items-center gap-1">
            <Avatar
              alt={editorInformation?.display_name}
              fallback={editorInformation?.display_name?.[0]?.toUpperCase()}
              src={getFileURL(editorInformation?.avatar_url ?? "")}
              size="2xs"
            />
            <span>{editorInformation?.display_name ?? t("common.deactivated_user")}</span>
          </Link>
          <span className="flex-shrink-0 text-tertiary">{timeAgo(page.updated_at ?? "")}</span>
        </div>
      </div>
      <div>
        <p className="text-11 font-medium text-tertiary">
          {t("page_navigation_pane.tabs.info.actors_info.created_by")}
        </p>
        <div className="mt-2 flex items-center justify-between gap-2 text-13 font-medium">
          <Link href={`/${workspaceSlug?.toString()}/profile/${page.created_by}`} className="flex items-center gap-1">
            <Avatar
              alt={creatorInformation?.display_name}
              fallback={creatorInformation?.display_name?.[0]?.toUpperCase()}
              src={getFileURL(creatorInformation?.avatar_url ?? "")}
              size="2xs"
            />
            <span>{creatorInformation?.display_name ?? t("common.deactivated_user")}</span>
          </Link>
          <span className="flex-shrink-0 text-tertiary">{formatDate(page.created_at)}</span>
        </div>
      </div>
    </div>
  );
});
