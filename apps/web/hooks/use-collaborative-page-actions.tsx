/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import type { TDocumentEventsServer } from "@plane/editor";
import type { TDocumentEventsClient } from "@plane/editor/lib";
import { DocumentCollaborativeEvents, getServerEventName } from "@plane/editor/lib";
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
// store
import type { TPageInstance } from "@/store/pages/base-page";

export type CollaborativeAction = {
  execute: (shouldSync?: boolean, recursive?: boolean) => Promise<void>;
  errorMessage: string;
};

type CollaborativeActionEvent =
  | { type: "sendMessageToServer"; message: TDocumentEventsServer; recursive?: boolean }
  | { type: "receivedMessageFromServer"; message: TDocumentEventsClient };

type Props = {
  page: TPageInstance;
};

export const useCollaborativePageActions = (props: Props) => {
  const { page } = props;
  const editorRef = page.editor.editorRef;
  // currentUserAction local state to track if the current action is being processed, a
  // local action is basically the action performed by the current user to avoid double operations
  const [currentActionBeingProcessed, setCurrentActionBeingProcessed] = useState<TDocumentEventsClient | null>(null);
  // translation
  const { t } = useTranslation();

  // @ts-expect-error - TODO: fix this
  const actionHandlerMap: Record<TDocumentEventsClient, CollaborativeAction> = useMemo(
    () => ({
      [DocumentCollaborativeEvents.lock.client]: {
        execute: (shouldSync?: boolean, recursive?: boolean) => page.lock({ shouldSync, recursive }),
        errorMessage: t("page_ui.operations.lock_error"),
      },
      [DocumentCollaborativeEvents.unlock.client]: {
        execute: (shouldSync?: boolean, recursive?: boolean) => page.unlock({ shouldSync, recursive }),
        errorMessage: t("page_ui.operations.unlock_error"),
      },
      [DocumentCollaborativeEvents.archive.client]: {
        execute: (shouldSync?: boolean) => page.archive({ shouldSync }),
        errorMessage: t("page_ui.operations.archive_error"),
      },
      [DocumentCollaborativeEvents.unarchive.client]: {
        execute: (shouldSync?: boolean) => page.restore({ shouldSync }),
        errorMessage: t("page_ui.operations.restore_error"),
      },
      [DocumentCollaborativeEvents["make-public"].client]: {
        execute: (shouldSync?: boolean) => page.makePublic({ shouldSync }),
        errorMessage: t("app_text.stores.page_make_public_error"),
      },
      [DocumentCollaborativeEvents["make-private"].client]: {
        execute: (shouldSync?: boolean) => page.makePrivate({ shouldSync }),
        errorMessage: t("app_text.stores.page_make_private_error"),
      },
    }),
    [page, t]
  );

  const executeCollaborativeAction = useCallback(
    async (event: CollaborativeActionEvent) => {
      const isPerformedByCurrentUser = event.type === "sendMessageToServer";
      const clientAction = isPerformedByCurrentUser ? DocumentCollaborativeEvents[event.message].client : event.message;
      const actionDetails = actionHandlerMap[clientAction];
      try {
        await actionDetails.execute(isPerformedByCurrentUser, isPerformedByCurrentUser ? event?.recursive : undefined);
        if (isPerformedByCurrentUser) {
          const serverEventName = getServerEventName(clientAction);
          if (serverEventName) {
            editorRef?.emitRealTimeUpdate(serverEventName);
          }
        }
      } catch {
        if (actionDetails?.errorMessage) {
          setToast({
            type: "error",
            title: t("toast.error"),
            message: actionDetails.errorMessage,
          });
        }
      }
    },
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- intentionally limited deps; behaviour unchanged
    [actionHandlerMap, editorRef]
  );

  useEffect(() => {
    const realTimeStatelessMessageListener = editorRef?.listenToRealTimeUpdate();
    const handleStatelessMessage = (message: { payload: TDocumentEventsClient }) => {
      if (currentActionBeingProcessed === message.payload) {
        setCurrentActionBeingProcessed(null);
        return;
      }

      if (message.payload) {
        executeCollaborativeAction({ type: "receivedMessageFromServer", message: message.payload });
      }
    };

    realTimeStatelessMessageListener?.on("stateless", handleStatelessMessage);

    return () => {
      realTimeStatelessMessageListener?.off("stateless", handleStatelessMessage);
    };
  }, [editorRef, currentActionBeingProcessed, executeCollaborativeAction]);

  return {
    executeCollaborativeAction,
  };
};
