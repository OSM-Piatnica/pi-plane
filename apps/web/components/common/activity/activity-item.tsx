/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";

import { useTranslation } from "@plane/i18n";
import type { TProjectActivity } from "@plane/types";
import { ActivityBlockComponent } from "./activity-block";
import { iconsMap, messages } from "./helper";

type TActivityItem = {
  activity: TProjectActivity;
  showProject?: boolean;
  ends?: "top" | "bottom" | undefined;
};

// One row of the project activity feed. Project activity is a commercial-edition feature: this fork's API
// does not record it and no screen here renders it (nothing imports this folder). The component and its
// translated sentences are kept so the records that edition produces display correctly.
export const ActivityItem = observer(function ActivityItem(props: TActivityItem) {
  const { activity, ends } = props;
  const { t } = useTranslation();

  if (!activity) return null;

  const activityType = activity.field;
  if (!activityType) return null;

  const { message, customUserName } = messages(activity, t);
  const icon = iconsMap[activityType] || iconsMap.default;

  return (
    <ActivityBlockComponent icon={icon} activity={activity} ends={ends} customUserName={customUserName}>
      <>{message}</>
    </ActivityBlockComponent>
  );
});
