/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// ui
import { useTranslation } from "@plane/i18n";
import { Avatar } from "@makeplane/propel/components/avatar";
import { EmptyStateCompact } from "@plane/blocks/empty-state";
import { Card } from "@plane/blocks/card";
import { Loader } from "@plane/blocks/skeleton";
import { getFileURL } from "@plane/utils";
// components
import { ActivityMessage } from "@/components/core/activity";
// constants
import { USER_PROFILE_ACTIVITY } from "@plane/constants";
// helpers
// hooks
import { useUser } from "@/hooks/store/user";
import { useLocalizedDates } from "@/hooks/use-localized-dates";
// services
import { UserService } from "@/services/user.service";

const userService = new UserService();

export const ProfileActivity = observer(function ProfileActivity() {
  const { timeAgo } = useLocalizedDates();
  const { workspaceSlug, userId } = useParams();
  // store hooks
  const { data: currentUser } = useUser();
  const { t } = useTranslation();

  const { data: userProfileActivity } = useSWR(
    workspaceSlug && userId ? USER_PROFILE_ACTIVITY(workspaceSlug.toString(), userId.toString(), {}) : null,
    workspaceSlug && userId
      ? () =>
          userService.getUserProfileActivity(workspaceSlug.toString(), userId.toString(), {
            per_page: 10,
          })
      : null
  );

  return (
    <div className="space-y-2">
      <h3 className="text-16 font-medium">{t("profile.stats.recent_activity.title")}</h3>
      <Card>
        {!userProfileActivity ? (
          <Loader className="space-y-5">
            <Loader.Item height="40px" />
            <Loader.Item height="40px" />
            <Loader.Item height="40px" />
            <Loader.Item height="40px" />
            <Loader.Item height="40px" />
          </Loader>
        ) : Array.isArray(userProfileActivity.results) && userProfileActivity.results.length > 0 ? (
          <div className="space-y-5">
            {userProfileActivity.results.map((activity) => (
              <div key={activity.id} className="flex gap-3">
                <Avatar
                  alt={activity.actor_detail?.display_name}
                  tooltip={activity.actor_detail?.display_name}
                  src={getFileURL(activity.actor_detail?.avatar_url)}
                  size="sm"
                />
                <div className="-mt-1 w-4/5 break-words">
                  <p className="inline text-13 text-secondary">
                    <span className="font-medium text-primary">
                      {currentUser?.id === activity.actor_detail?.id
                        ? t("activity_feed.profile.you")
                        : activity.actor_detail?.display_name}
                    </span>
                    {t("activity_feed.profile.actor_separator")}
                    <ActivityMessage activity={activity} showIssue />
                  </p>
                  <p className="text-11 whitespace-nowrap text-secondary">{timeAgo(activity.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyStateCompact title={t("no_data_yet")} assetKey="unknown" assetClassName="size-20" />
        )}
      </Card>
    </div>
  );
});
