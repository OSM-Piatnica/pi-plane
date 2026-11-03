/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { useTranslation } from "@plane/i18n";
import type { TNotification } from "@plane/types";
// helpers
import { renderTaggedText } from "@/helpers/tagged-text";

/**
 * The text of the inbox entry about a work item that was assigned to a group of the person: to the admins of the
 * group (who always hear about it) and to the members who asked to.
 */
export function GroupAssignmentNotificationContent({ notification }: { notification: TNotification }) {
  const { t } = useTranslation();
  const { data, triggered_by_details: triggeredBy } = notification;
  const groupName = data?.group_assignment?.group.name ?? "";
  const textKey =
    data?.group_assignment?.role === "admin"
      ? "notification.group_assignment.admin"
      : "notification.group_assignment.member";

  return (
    <>
      <span className="font-medium text-primary">
        {triggeredBy?.is_bot ? triggeredBy.first_name : triggeredBy?.display_name}{" "}
      </span>
      <span className="text-tertiary">
        {renderTaggedText(t(textKey), {
          value: () => <span className="font-medium text-primary">{groupName}</span>,
        })}
      </span>
      {t("notification.content.end_punctuation")}
    </>
  );
}
