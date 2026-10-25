/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { useTranslation } from "@plane/i18n";
import type { TNotification } from "@plane/types";
// helpers
import { getAccessRequestNotificationTextKey } from "@/helpers/access-request-notification";
import { renderTaggedText } from "@/helpers/tagged-text";

/**
 * The text of the inbox entry about a request to join a Private project: that someone asked, to the admins who
 * decide, or how it was decided, to the person who asked.
 */
export function AccessRequestNotificationContent({ notification }: { notification: TNotification }) {
  const { t } = useTranslation();
  const { data, triggered_by_details: triggeredBy } = notification;
  const projectName = data?.project?.name ?? "";

  return (
    <>
      <span className="font-medium text-primary">
        {triggeredBy?.is_bot ? triggeredBy.first_name : triggeredBy?.display_name}{" "}
      </span>
      <span className="text-tertiary">
        {renderTaggedText(t(getAccessRequestNotificationTextKey(data?.access_request?.status)), {
          value: () => <span className="font-medium text-primary">{projectName}</span>,
        })}
      </span>
      {t("notification.content.end_punctuation")}
    </>
  );
}
