/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import type { TNotification } from "@plane/types";

/** The text of the inbox entry about a message somebody wrote to the admins of the workspace. */
export function AdminMessageNotificationContent({ notification }: { notification: TNotification }) {
  const { t } = useTranslation();
  const { triggered_by_details: triggeredBy } = notification;

  return (
    <>
      <span className="font-medium text-primary">
        {triggeredBy?.is_bot ? triggeredBy.first_name : triggeredBy?.display_name}{" "}
      </span>
      <span className="text-tertiary">{t("contact_workspace_admins.notification_text")}</span>
      {t("notification.content.end_punctuation")}
    </>
  );
}
