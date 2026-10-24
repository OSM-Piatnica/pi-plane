/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TNotification } from "@plane/types";
import {
  convertMinutesToHoursMinutesString,
  renderFormattedDate,
  sanitizeCommentForNotification,
  stripAndTruncateHTML,
} from "@plane/utils";
// components
import { LiteTextEditor } from "@/components/editor/lite-text";
import {
  ADDITIONAL_NOTIFICATION_CONTENT_MAP,
  renderAdditionalAction,
  renderAdditionalValue,
} from "@/components/workspace-notifications/notification-card/content";
import { renderTaggedText } from "@/helpers/tagged-text";
import { useLocalizedDates } from "@/hooks/use-localized-dates";

// Types
export type TNotificationFieldData = {
  field: string | undefined;
  newValue: string | undefined;
  oldValue: string | undefined;
  verb: string | undefined;
  /** Formats a date in the user's language; English style when omitted. */
  formatDate?: (date: string | undefined) => string | undefined;
  /** Translates the action text of the notification. */
  t: (key: string) => string;
};

export type TNotificationContentDetails = {
  action?: ReactNode;
  value?: ReactNode;
};

export type TNotificationContentHandler = (data: TNotificationFieldData) => TNotificationContentDetails | null;

export type TNotificationContentMap = {
  [key: string]: TNotificationContentHandler;
};

// Base notification content map for core fields. Each action is a full phrase, including the word that links it to
// the value that follows ("changed the state to"), because that word and its place differ between languages.
export const BASE_NOTIFICATION_CONTENT_MAP: TNotificationContentMap = {
  duplicate: ({ verb, t }) => ({
    action:
      verb === "created" ? t("notification.content.duplicate_added") : t("notification.content.duplicate_removed"),
    value: null,
  }),
  assignees: ({ newValue, oldValue, t }) => ({
    action: newValue !== "" ? t("notification.content.assignee_added") : t("notification.content.assignee_removed"),
    value: newValue !== "" ? newValue : oldValue,
  }),
  start_date: ({ newValue, formatDate, t }) => ({
    action: newValue !== "" ? t("notification.content.start_date_set") : t("notification.content.start_date_removed"),
    value: (formatDate ?? renderFormattedDate)(newValue),
  }),
  target_date: ({ newValue, formatDate, t }) => ({
    action: newValue !== "" ? t("notification.content.due_date_set") : t("notification.content.due_date_removed"),
    value: (formatDate ?? renderFormattedDate)(newValue),
  }),
  duration: ({ newValue, t }) => ({
    action: newValue !== "" ? t("notification.content.duration_set") : t("notification.content.duration_removed"),
    value: newValue,
  }),
  labels: ({ newValue, oldValue, t }) => ({
    action: newValue !== "" ? t("notification.content.label_added") : t("notification.content.label_removed"),
    value: newValue !== "" ? newValue : oldValue,
  }),
  parent: ({ newValue, oldValue, t }) => ({
    action: newValue !== "" ? t("notification.content.parent_added") : t("notification.content.parent_removed"),
    value: newValue !== "" ? newValue : oldValue,
  }),
  relates_to: ({ t }) => ({
    action: t("notification.content.relates_to"),
    value: null,
  }),
  comment: ({ newValue, t }, renderCommentBox?: boolean) => ({
    action: t("notification.content.commented"),
    value: renderCommentBox ? null : sanitizeCommentForNotification(newValue),
  }),
  archived_at: ({ newValue, t }) => ({
    action: newValue === "restore" ? t("notification.content.restored") : t("notification.content.archived"),
    value: null,
  }),
  // a work item that was created and assigned to the receiver has no field
  None: ({ t }) => ({
    action: t("notification.content.created_and_assigned"),
    value: null,
  }),
  mention: ({ t }) => ({
    action: t("notification.content.mentioned_you"),
    value: null,
  }),
  description: ({ newValue, t }) => ({
    action: t("notification.content.description_updated"),
    value: stripAndTruncateHTML(newValue || "", 55),
  }),
  estimate_time: ({ newValue, oldValue, t }) => ({
    action: t("notification.content.estimate_updated"),
    value:
      newValue !== ""
        ? convertMinutesToHoursMinutesString(Number(newValue))
        : convertMinutesToHoursMinutesString(Number(oldValue)),
  }),
};

// Helper to get content details from maps
const getNotificationContentDetails = (
  fieldData: TNotificationFieldData,
  renderCommentBox?: boolean
): TNotificationContentDetails | null => {
  const { field } = fieldData;
  if (!field) return null;

  // Check base map first
  const baseHandler = BASE_NOTIFICATION_CONTENT_MAP[field];
  if (baseHandler) {
    // Special case for comment field that needs renderCommentBox
    if (field === "comment") {
      return (baseHandler as (data: TNotificationFieldData, renderCommentBox?: boolean) => TNotificationContentDetails)(
        fieldData,
        renderCommentBox
      );
    }
    return baseHandler(fieldData);
  }

  // Check additional map (EE extensions)
  const additionalHandler = ADDITIONAL_NOTIFICATION_CONTENT_MAP[field];
  if (additionalHandler) {
    return additionalHandler(fieldData);
  }

  return null;
};

export function NotificationContent({
  notification,
  workspaceId,
  workspaceSlug,
  projectId,
  renderCommentBox = false,
}: {
  notification: TNotification;
  workspaceId: string;
  workspaceSlug: string;
  projectId: string;
  renderCommentBox?: boolean;
}) {
  const { formatDate } = useLocalizedDates();
  const { t } = useTranslation();
  const { data, triggered_by_details: triggeredBy } = notification;
  const notificationField = data?.issue_activity?.field;
  const newValue = data?.issue_activity?.new_value;
  const oldValue = data?.issue_activity?.old_value;
  const verb = data?.issue_activity?.verb;

  const fieldData: TNotificationFieldData = {
    field: notificationField,
    newValue,
    oldValue,
    verb,
    formatDate,
    t,
  };

  const renderTriggerName = () => (
    <span className="font-medium text-primary">
      {triggeredBy?.is_bot ? triggeredBy.first_name : triggeredBy?.display_name}{" "}
    </span>
  );

  // Get content details from map
  const contentDetails = getNotificationContentDetails(fieldData, renderCommentBox);

  // Render action - use map value if defined, otherwise fall through to default handler
  // Note: undefined = fall through to default, null = explicitly no action text
  const renderAction = (): ReactNode => {
    if (!notificationField) return "";
    // Check if action is explicitly defined in map (including null)
    if (contentDetails && "action" in contentDetails) return contentDetails.action;
    // Fallback to default action handler for fields not in map or without action defined
    return renderAdditionalAction(notificationField, verb, t);
  };

  // Render value - use map value if defined, otherwise fall through to default handler
  const renderValue = (): ReactNode => {
    // Check if value is explicitly defined in map
    if (contentDetails && "value" in contentDetails) return contentDetails.value;
    // Fallback to default value handler for fields not in map or without value defined
    return renderAdditionalValue(notificationField, newValue, oldValue);
  };

  const actionNode = renderAction();
  const valueNode = verb === "deleted" ? null : renderValue();
  // a translation can place the value inside the phrase (`<value/>`), where the word order of its language needs it
  const hasInlineValue = typeof actionNode === "string" && actionNode.includes("<value/>");

  return (
    <>
      {renderTriggerName()}
      <span className="text-tertiary">
        {hasInlineValue
          ? renderTaggedText(actionNode, {
              value: () => <span className="font-medium text-primary">{valueNode}</span>,
            })
          : actionNode}{" "}
      </span>
      {verb !== "deleted" && (
        <>
          {!hasInlineValue && <span className="font-medium text-primary">{valueNode}</span>}
          {notificationField === "comment" && renderCommentBox && (
            <div className="origin-left scale-75">
              <LiteTextEditor
                editable={false}
                id=""
                initialValue={newValue ?? ""}
                workspaceId={workspaceId}
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                displayConfig={{
                  fontSize: "small-font",
                }}
              />
            </div>
          )}
          {t("notification.content.end_punctuation")}
        </>
      )}
    </>
  );
}
