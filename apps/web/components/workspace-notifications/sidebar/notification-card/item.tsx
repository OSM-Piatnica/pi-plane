/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { useState } from "react";
import { observer } from "mobx-react";
import { ClockOutline } from "@makeplane/propel/icons";
// plane imports
import { Avatar } from "@makeplane/propel/components/avatar";
import { Row } from "@plane/blocks/layout";
import { cn, getFileURL } from "@plane/utils";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";
import { useLocalizedDates } from "@/hooks/use-localized-dates";
import { useNotification } from "@/hooks/store/notifications/use-notification";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useAppRouter } from "@/hooks/use-app-router";
import { useWorkspace } from "@/hooks/store/use-workspace";
// local imports
import { getAccessRequestNotificationPath } from "@/helpers/access-request-notification";
import { AccessRequestNotificationContent } from "./access-request-content";
import { AdminMessageModal } from "./admin-message-modal";
import { AdminMessageNotificationContent } from "./admin-message-content";
import { NotificationContent } from "./content";
import { NotificationOption } from "./options";

type TNotificationItem = {
  workspaceSlug: string;
  notificationId: string;
};

export const NotificationItem = observer(function NotificationItem(props: TNotificationItem) {
  const { t } = useTranslation();
  const { formatDate, formatTime, timeAgo } = useLocalizedDates();
  const { workspaceSlug, notificationId } = props;
  // hooks
  const { currentSelectedNotificationId, setCurrentSelectedNotificationId } = useWorkspaceNotifications();
  const { asJson: notification, markNotificationAsRead } = useNotification(notificationId);
  const { getIsIssuePeeked, setPeekIssue } = useIssueDetail();
  const { getWorkspaceBySlug } = useWorkspace();
  const router = useAppRouter();
  // states
  const [isSnoozeStateModalOpen, setIsSnoozeStateModalOpen] = useState(false);
  const [customSnoozeModal, setCustomSnoozeModal] = useState(false);
  const [isAdminMessageOpen, setIsAdminMessageOpen] = useState(false);

  // derived values
  const projectId = notification?.project || undefined;
  const issueId = notification?.data?.issue?.id || undefined;
  const workspace = getWorkspaceBySlug(workspaceSlug);

  const notificationField = notification?.data?.issue_activity?.field || undefined;
  // a request to join a Private project has no work item: a click opens where the request waits or where it led
  const isAccessRequest = notification?.entity_name === "project_access_request" && !!notification?.data?.project;
  // a message somebody wrote to the admins has no work item and no project either: a click opens the whole message
  const isAdminMessage =
    notification?.entity_name === "workspace_admin_message" && !!notification?.data?.workspace_admin_message;
  const notificationTriggeredBy = notification.triggered_by_details || undefined;

  const handleNotificationIssuePeekOverview = async () => {
    if (workspaceSlug && projectId && issueId && !isSnoozeStateModalOpen && !customSnoozeModal) {
      setPeekIssue(undefined);
      setCurrentSelectedNotificationId(notificationId);

      // make the notification as read
      if (notification.read_at === null) {
        try {
          await markNotificationAsRead(workspaceSlug);
        } catch (error) {
          console.error(error);
        }
      }

      if (notification?.is_inbox_issue === false) {
        if (!getIsIssuePeeked(issueId)) {
          setPeekIssue({ workspaceSlug, projectId, issueId });
        }
      }
    }
  };

  const handleNotificationAccessRequest = async () => {
    if (!workspaceSlug || !projectId || isSnoozeStateModalOpen || customSnoozeModal) return;
    setCurrentSelectedNotificationId(notificationId);
    if (notification.read_at === null) {
      try {
        await markNotificationAsRead(workspaceSlug);
      } catch (error) {
        console.error(error);
      }
    }
    router.push(getAccessRequestNotificationPath(notification.data?.access_request?.status, workspaceSlug, projectId));
  };

  const handleAdminMessage = async () => {
    if (!workspaceSlug || isSnoozeStateModalOpen || customSnoozeModal) return;
    setCurrentSelectedNotificationId(notificationId);
    setIsAdminMessageOpen(true);
    if (notification.read_at === null) {
      try {
        await markNotificationAsRead(workspaceSlug);
      } catch (error) {
        console.error(error);
      }
    }
  };

  if (
    !workspaceSlug ||
    !notificationId ||
    !notification?.id ||
    (!notificationField && !isAccessRequest && !isAdminMessage) ||
    !workspace?.id ||
    (!projectId && !isAdminMessage)
  )
    return <></>;

  return (
    <>
      <Row
        className={cn(
          "group relative flex cursor-pointer items-center gap-2 border-b border-subtle py-4 transition-all",
          {
            "bg-layer-1/30": currentSelectedNotificationId === notification?.id,
            "bg-accent-primary/5": notification.read_at === null,
          }
        )}
        onClick={
          isAdminMessage
            ? handleAdminMessage
            : isAccessRequest
              ? handleNotificationAccessRequest
              : handleNotificationIssuePeekOverview
        }
      >
        {notification.read_at === null && (
          <div className="absolute top-[50%] left-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-accent-primary" />
        )}

        <div className="relative flex w-full gap-2">
          <div className="relative flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-layer-1">
            {notificationTriggeredBy && (
              <Avatar
                alt={notificationTriggeredBy.display_name || notificationTriggeredBy?.first_name}
                fallback={(notificationTriggeredBy.display_name ||
                  notificationTriggeredBy?.first_name)?.[0]?.toUpperCase()}
                src={getFileURL(notificationTriggeredBy.avatar_url)}
                size="xl"
              />
            )}
          </div>

          <div className="-mt-2 w-full space-y-1">
            <div className="relative flex h-8 items-center gap-3">
              <div className="line-clamp-1 w-full truncate overflow-hidden text-body-xs-medium break-all whitespace-normal text-primary">
                {isAdminMessage ? (
                  <AdminMessageNotificationContent notification={notification} />
                ) : isAccessRequest ? (
                  <AccessRequestNotificationContent notification={notification} />
                ) : (
                  <NotificationContent
                    notification={notification}
                    workspaceId={workspace.id}
                    workspaceSlug={workspaceSlug}
                    projectId={projectId ?? ""}
                  />
                )}
              </div>
              <NotificationOption
                workspaceSlug={workspaceSlug}
                notificationId={notification?.id}
                isSnoozeStateModalOpen={isSnoozeStateModalOpen}
                setIsSnoozeStateModalOpen={setIsSnoozeStateModalOpen}
                customSnoozeModal={customSnoozeModal}
                setCustomSnoozeModal={setCustomSnoozeModal}
              />
            </div>

            <div className="relative flex items-center gap-3 text-caption-sm-regular text-secondary">
              <div className="line-clamp-1 w-full truncate overflow-hidden break-words whitespace-normal">
                {isAdminMessage ? (
                  notification?.data?.workspace_admin_message?.message
                ) : isAccessRequest ? (
                  notification?.data?.project?.name
                ) : (
                  <>
                    {notification?.data?.issue?.identifier}-{notification?.data?.issue?.sequence_id}&nbsp;
                    {notification?.data?.issue?.name}
                  </>
                )}
              </div>
              <div className="flex-shrink-0">
                {notification?.snoozed_till ? (
                  <p className="flex flex-shrink-0 items-center justify-end gap-x-1 text-tertiary">
                    <ClockOutline className="h-4 w-4" />
                    <span>
                      {t("date_phrases.till", {
                        date: formatDate(notification.snoozed_till),
                        time: formatTime(notification.snoozed_till, "12-hour"),
                      })}
                    </span>
                  </p>
                ) : (
                  <p className="mt-auto flex-shrink-0 text-tertiary">
                    {notification.created_at && timeAgo(notification.created_at)}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </Row>
      {isAdminMessage && (
        <AdminMessageModal
          notification={notification}
          isOpen={isAdminMessageOpen}
          onClose={() => setIsAdminMessageOpen(false)}
        />
      )}
    </>
  );
});
