/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { useTranslation } from "@plane/i18n";
import type { TNotification } from "@plane/types";
// helpers
import { getGroupMembershipNotificationTextKey } from "@/helpers/group-membership-notification";
import { renderTaggedText } from "@/helpers/tagged-text";

/** The text of the inbox entry about being added to a group, or about a change of the person's role in it. */
export function GroupMembershipNotificationContent({ notification }: { notification: TNotification }) {
  const { t } = useTranslation();
  const { data, triggered_by_details: triggeredBy } = notification;
  const groupName = data?.group_membership?.group.name ?? "";

  return (
    <>
      <span className="font-medium text-primary">
        {triggeredBy?.is_bot ? triggeredBy.first_name : triggeredBy?.display_name}{" "}
      </span>
      <span className="text-tertiary">
        {renderTaggedText(t(getGroupMembershipNotificationTextKey(data?.group_membership)), {
          value: () => <span className="font-medium text-primary">{groupName}</span>,
        })}
      </span>
      {t("notification.content.end_punctuation")}
    </>
  );
}
